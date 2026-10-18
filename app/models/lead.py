import enum
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.core.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    QUALIFIED = "Qualified"
    QUOTATION_SENT = "Quotation Sent"
    WON = "Won"
    LOST = "Lost"


class ContactLead(Base):
    """
    Inbound customer contact inquiry from public contact forms, footer forms, or landing pages.
    """
    __tablename__ = "contact_leads"

    name = Column(String(150), nullable=False)
    company = Column(String(150), nullable=True)
    email = Column(String(150), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    source = Column(String(100), default="contact_page", nullable=False)
    client_ip = Column(String(100), nullable=True)
    status = Column(String(50), default=LeadStatus.NEW.value, nullable=False, index=True)
    @property
    def ip_address(self) -> Optional[str]:
        return self.client_ip

    @ip_address.setter
    def ip_address(self, val: Optional[str]):
        self.client_ip = val

    def __repr__(self) -> str:
        return f"<ContactLead id={self.id} name='{self.name}' status='{self.status}'>"


class QuoteRequest(Base):
    """
    Engineering Request For Quote (RFQ) with product specifications and drawing uploads.
    """
    __tablename__ = "quote_requests"

    customer_name = Column(String(150), nullable=False)
    company = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    product_component = Column(String(200), nullable=True)
    material = Column(String(150), nullable=True)
    quantity = Column(String(100), nullable=True)
    required_delivery = Column(String(100), nullable=True)
    drawing_file = Column(String(500), nullable=True)
    additional_requirements = Column(Text, nullable=True)
    source = Column(String(100), default="request_quote_page", nullable=False)
    client_ip = Column(String(100), nullable=True)
    status = Column(String(50), default=LeadStatus.NEW.value, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    @property
    def name(self) -> str:
        return self.customer_name

    @name.setter
    def name(self, val: str):
        self.customer_name = val

    @property
    def product(self) -> Optional[str]:
        return self.product_component

    @product.setter
    def product(self, val: Optional[str]):
        self.product_component = val

    @property
    def requirement(self) -> Optional[str]:
        return self.additional_requirements

    @requirement.setter
    def requirement(self, val: Optional[str]):
        self.additional_requirements = val

    @property
    def ip_address(self) -> Optional[str]:
        return self.client_ip

    @ip_address.setter
    def ip_address(self, val: Optional[str]):
        self.client_ip = val

    def __repr__(self) -> str:
        return f"<QuoteRequest id={self.id} customer='{self.customer_name}' status='{self.status}'>"
