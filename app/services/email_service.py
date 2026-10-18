import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.models.lead import ContactLead, QuoteRequest


class EmailServiceInterface(ABC):
    """Abstract interface for application email dispatching."""

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    def send_contact_notification(self, lead: ContactLead) -> bool:
        pass

    @abstractmethod
    def send_contact_acknowledgment(self, lead: ContactLead) -> bool:
        pass

    @abstractmethod
    def send_quote_notification(self, quote: QuoteRequest) -> bool:
        pass

    @abstractmethod
    def send_quote_acknowledgment(self, quote: QuoteRequest) -> bool:
        pass

    @abstractmethod
    def send_admin_notification(self, subject: str, message: str) -> bool:
        pass


class SMTPEmailService(EmailServiceInterface):
    """Production SMTP email delivery implementation."""

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    def clear_sent_buffer(self):
        self.sent_messages.clear()

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        return self.sent_messages

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        record = {
            "to": to_email,
            "to_email": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "html_body": body_html,
        }
        self.sent_messages.append(record)

        # In dev or if credentials aren't set, log and return success
        if not settings.MAIL_USERNAME or not settings.MAIL_SERVER or settings.is_development:
            logger.info(
                f"[EMAIL SERVICE - SIMULATED] To: {to_email} | Subject: '{subject}'"
            )
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.MAIL_FROM
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            if settings.MAIL_SSL:
                server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10)
                if settings.MAIL_TLS:
                    server.starttls()

            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)

            server.sendmail(settings.MAIL_FROM, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Email dispatched successfully to {to_email}")
            return True
        except Exception as exc:
            logger.error(f"Failed to dispatch email to {to_email}: {exc}")
            return False

    def send_contact_notification(self, lead: Optional[ContactLead] = None, **kwargs) -> bool:
        admin_email = settings.FIRST_SUPERADMIN_EMAIL
        name = lead.name if lead else kwargs.get("name", "Website Visitor")
        company = (lead.company if lead else kwargs.get("company")) or "Individual"
        email = lead.email if lead else kwargs.get("email", "")
        phone = (lead.phone if lead else kwargs.get("phone")) or "N/A"
        country = (lead.country if lead else kwargs.get("country")) or "N/A"
        source = (lead.source if lead else kwargs.get("source")) or "Public Contact Form"
        message = lead.message if lead else kwargs.get("message", "")

        subject = f"[New Lead] Contact Form: {name} ({company})"
        text = f"""New Contact Form Submission:
Name: {name}
Company: {company}
Email: {email}
Phone: {phone}
Country: {country}
Source: {source}

Message:
{message}
"""
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #E2E8F0; border-radius: 6px;">
<h2 style="color: #17212B; margin-top: 0;">New Inbound Contact Lead</h2>
<p><strong>Name:</strong> {name}</p>
<p><strong>Company:</strong> {company}</p>
<p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
<p><strong>Phone:</strong> {phone}</p>
<p><strong>Country:</strong> {country}</p>
<p><strong>Source:</strong> {source}</p>
<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 20px 0;">
<p><strong>Message:</strong></p>
<p style="background: #F8FAFC; padding: 12px; border-radius: 4px; border-left: 3px solid #B7793F;">{message}</p>
</div>"""
        return self.send_email(admin_email, subject, text, html)

    def send_contact_acknowledgment(self, lead: Optional[ContactLead] = None, **kwargs) -> bool:
        name = lead.name if lead else kwargs.get("name", "Valued Customer")
        to_email = lead.email if lead else kwargs.get("to_email", kwargs.get("email", ""))
        message = (lead.message if lead else kwargs.get("message")) or ""
        subject = f"Thank you for contacting {settings.APP_NAME}"
        text = f"""Hello {name},

Thank you for contacting {settings.APP_NAME}. We have received your inquiry and our engineering sales team will review your requirements and respond within 1 business day.

Your Message Summary:
{message}

Best regards,
Precision Engineering & Forging Team
"""
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #E2E8F0; border-radius: 6px;">
<h2 style="color: #17212B; margin-top: 0;">Thank You for Reaching Out</h2>
<p>Hello {name},</p>
<p>Thank you for contacting <strong>{settings.APP_NAME}</strong>. We have received your inquiry and our technical engineering team will review your specifications and follow up within one business day.</p>
<div style="background: #F8FAFC; padding: 15px; border-left: 3px solid #B7793F; margin: 20px 0;">
  <strong>Your Inquiry:</strong>
  <p style="margin-bottom: 0;">{message}</p>
</div>
<p style="color: #64748B; font-size: 0.9rem;">This is an automated acknowledgment. Please do not reply directly to this email.</p>
</div>"""
        return self.send_email(to_email, subject, text, html)

    def send_user_acknowledgment(self, to_email: Optional[str] = None, name: Optional[str] = None, submission_type: Optional[str] = None, lead: Optional[ContactLead] = None, **kwargs) -> bool:
        """Alias for general acknowledgment notifications."""
        target_name = name or (lead.name if lead else "Valued Customer")
        target_email = to_email or (lead.email if lead else "")
        subject = f"Thank You for Contacting Us - {settings.APP_NAME}"
        text = f"Hello {target_name},\n\nWe have received your {submission_type or 'inquiry'} and our engineering team will follow up within 24 hours."
        html = f"""<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #E2E8F0; border-radius: 6px;">
<h2>Thank You for Contacting Us</h2>
<p>Hello {target_name},</p>
<p>We have received your {submission_type or 'inquiry'} and our engineering team will follow up within 24 hours.</p>
</div>"""
        return self.send_email(target_email, subject, text, html)

    def send_quote_notification(self, quote: Optional[QuoteRequest] = None, **kwargs) -> bool:
        admin_email = settings.FIRST_SUPERADMIN_EMAIL
        name = (quote.customer_name if quote else kwargs.get("name")) or "Prospective Client"
        company = (quote.company if quote else kwargs.get("company")) or "N/A"
        email = (quote.email if quote else kwargs.get("email")) or ""
        phone = (quote.phone if quote else kwargs.get("phone")) or "N/A"
        country = (quote.country if quote else kwargs.get("country")) or "N/A"
        product = (quote.product_component if quote else kwargs.get("product", kwargs.get("product_component"))) or "Custom Forging"
        material = (quote.material if quote else kwargs.get("material")) or "N/A"
        quantity = (quote.quantity if quote else kwargs.get("quantity")) or "N/A"
        delivery = (quote.required_delivery if quote else kwargs.get("required_delivery")) or "N/A"
        drawing = (quote.drawing_file if quote else kwargs.get("drawing_file")) or "No file attached"
        reqs = (quote.additional_requirements if quote else kwargs.get("requirement", kwargs.get("additional_requirements"))) or "None"

        subject = f"[New RFQ] Quote Request from {name} ({company})"
        text = f"""New Request For Quote Received:
Customer: {name}
Company: {company}
Email: {email}
Phone: {phone}
Country: {country}

Product / Component: {product}
Material Grade: {material}
Quantity: {quantity}
Required Delivery: {delivery}
Drawing File: {drawing}

Additional Requirements:
{reqs}
"""
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #E2E8F0; border-radius: 6px;">
<h2 style="color: #17212B; margin-top: 0;">New Request for Quote (RFQ)</h2>
<table style="width: 100%; border-collapse: collapse;">
  <tr><td style="padding: 6px 0; color: #64748B; width: 140px;">Customer:</td><td style="font-weight: 600;">{name}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Company:</td><td style="font-weight: 600;">{company}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Email:</td><td><a href="mailto:{email}">{email}</a></td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Phone:</td><td>{phone}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Country:</td><td>{country}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Component:</td><td>{product}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Material:</td><td>{material}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Quantity:</td><td>{quantity}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Delivery:</td><td>{delivery}</td></tr>
  <tr><td style="padding: 6px 0; color: #64748B;">Drawing:</td><td>{'<a href="' + drawing + '">View Attached Drawing</a>' if drawing != 'No file attached' else 'None attached'}</td></tr>
</table>
<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 20px 0;">
<p><strong>Additional Requirements:</strong></p>
<p style="background: #F8FAFC; padding: 12px; border-radius: 4px; border-left: 3px solid #B7793F;">{reqs}</p>
</div>"""
        return self.send_email(admin_email, subject, text, html)

    def send_quote_acknowledgment(self, quote: QuoteRequest) -> bool:
        subject = f"Quote Request Acknowledgment - {quote.company} | {settings.APP_NAME}"
        text = f"""Hello {quote.customer_name},

Thank you for submitting a Request for Quote to {settings.APP_NAME}.

We have received your specifications for {quote.product_component or 'forged components'}. Our metallurgical and estimation engineering department is reviewing your requirements and drawing files.

You will receive an official commercial proposal and production timeline within 2 business days.

Best regards,
Estimation & Engineering Sales
{settings.APP_NAME}
"""
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #E2E8F0; border-radius: 6px;">
<h2 style="color: #17212B; margin-top: 0;">Quote Request Received</h2>
<p>Hello {quote.customer_name},</p>
<p>Thank you for submitting your engineering Request for Quote to <strong>{settings.APP_NAME}</strong>.</p>
<p>We have logged your request for <strong>{quote.product_component or 'Forged Precision Components'}</strong> ({quote.quantity or 'N/A'} units in {quote.material or 'specified grade'}).</p>
<p>Our engineering estimation team is reviewing your tolerances, manufacturing processes, and metallurgy. We will prepare an official commercial quotation within two business days.</p>
<p style="color: #64748B; font-size: 0.9rem; margin-top: 30px;">Direct Engineering Contact: sales@forgingcms.com | +91 0000000000</p>
</div>"""
        return self.send_email(quote.email, subject, text, html)

    def send_admin_notification(self, subject: str, message: str) -> bool:
        admin_email = settings.FIRST_SUPERADMIN_EMAIL
        return self.send_email(admin_email, subject, message)


email_service = SMTPEmailService()
