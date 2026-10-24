import xml.sax.saxutils as saxutils
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.product import Product, ProductCategory
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.material import Material
from app.models.infrastructure import Equipment, Facility
from app.models.quality import Certification
from app.models.blog import BlogPost, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.page import CMSPage, PageStatus


class SitemapService:
    """
    Automated XML Sitemap generation service conforming to sitemaps.org standards.
    Excludes admin, authentication, private content, and unpublished drafts.
    """

    def generate_sitemap_xml(self, db: Session, base_url: Optional[str] = None) -> str:
        root_url = (base_url or settings.SITE_URL or "http://localhost:8000").rstrip("/")
        seen_urls: Set[str] = set()
        entries: List[Dict[str, str]] = []

        def add_entry(path: str, changefreq: str = "weekly", priority: str = "0.8", lastmod: Optional[str] = None):
            clean_path = path if path.startswith("/") else f"/{path}"
            full_url = f"{root_url}{clean_path}".lower()
            if full_url in seen_urls:
                return
            # Strict safety check: Never include admin, login, private or api in sitemap
            for private_prefix in ["/admin", "/login", "/api", "/uploads/private", "/uploads/drawings"]:
                if clean_path.startswith(private_prefix):
                    return

            seen_urls.add(full_url)
            entry = {
                "loc": full_url,
                "changefreq": changefreq,
                "priority": priority,
            }
            if lastmod:
                entry["lastmod"] = lastmod
            entries.append(entry)

        # 1. High-Priority Corporate & Marketing Landing Pages
        add_entry("/", changefreq="daily", priority="1.0")
        add_entry("/about", changefreq="weekly", priority="0.9")
        add_entry("/company-history", changefreq="monthly", priority="0.8")
        add_entry("/products", changefreq="daily", priority="0.9")
        add_entry("/capabilities", changefreq="weekly", priority="0.8")
        add_entry("/industries", changefreq="weekly", priority="0.8")
        add_entry("/infrastructure", changefreq="monthly", priority="0.8")
        add_entry("/machinery", changefreq="weekly", priority="0.8")
        add_entry("/materials", changefreq="weekly", priority="0.8")
        add_entry("/quality", changefreq="monthly", priority="0.8")
        add_entry("/certifications", changefreq="monthly", priority="0.8")
        add_entry("/faqs", changefreq="weekly", priority="0.7")
        add_entry("/blog", changefreq="daily", priority="0.8")
        add_entry("/case-studies", changefreq="weekly", priority="0.8")
        add_entry("/downloads", changefreq="weekly", priority="0.7")
        add_entry("/contact", changefreq="monthly", priority="0.8")
        add_entry("/request-a-quote", changefreq="weekly", priority="0.9")

        # 2. Active Product Categories
        categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).all()
        for cat in categories:
            mod = cat.updated_at.strftime("%Y-%m-%d") if hasattr(cat, "updated_at") and cat.updated_at else None
            add_entry(f"/products/{cat.slug}", changefreq="weekly", priority="0.8", lastmod=mod)

        # 3. Published Products
        products = db.query(Product).filter(Product.status == "published").all()
        for prod in products:
            cat_slug = prod.category.slug if prod.category else "all"
            mod = None
            if hasattr(prod, "updated_at") and prod.updated_at:
                mod = prod.updated_at.strftime("%Y-%m-%d")
            elif hasattr(prod, "created_at") and prod.created_at:
                mod = prod.created_at.strftime("%Y-%m-%d")
            add_entry(f"/products/{cat_slug}/{prod.slug}", changefreq="weekly", priority="0.8", lastmod=mod)

        # 4. Published Capabilities
        capabilities = db.query(Capability).filter(Capability.status == "published").all()
        for cap in capabilities:
            mod = cap.updated_at.strftime("%Y-%m-%d") if hasattr(cap, "updated_at") and cap.updated_at else None
            add_entry(f"/capabilities/{cap.slug}", changefreq="monthly", priority="0.7", lastmod=mod)

        # 5. Published Industries
        industries = db.query(Industry).filter(Industry.status == "published").all()
        for ind in industries:
            mod = ind.updated_at.strftime("%Y-%m-%d") if hasattr(ind, "updated_at") and ind.updated_at else None
            add_entry(f"/industries/{ind.slug}", changefreq="monthly", priority="0.7", lastmod=mod)

        # 6. Published Materials
        materials = db.query(Material).filter(Material.status == "published").all()
        for mat in materials:
            mod = mat.updated_at.strftime("%Y-%m-%d") if hasattr(mat, "updated_at") and mat.updated_at else None
            add_entry(f"/materials/{mat.slug}", changefreq="monthly", priority="0.7", lastmod=mod)

        # 7. Published Equipment / Machinery items
        equipment_items = db.query(Equipment).filter(Equipment.status == "published").all()
        for eq in equipment_items:
            slug = getattr(eq, "slug", None)
            if slug:
                mod = eq.updated_at.strftime("%Y-%m-%d") if hasattr(eq, "updated_at") and eq.updated_at else None
                add_entry(f"/machinery/{slug}", changefreq="monthly", priority="0.7", lastmod=mod)

        # 8. Published Blog Articles (strictly excludes scheduled future posts and drafts)
        now = datetime.now(timezone.utc)
        blog_posts = db.query(BlogPost).filter(
            BlogPost.status == BlogPostStatus.PUBLISHED.value,
            BlogPost.publish_date <= now,
        ).all()
        for post in blog_posts:
            mod = None
            if hasattr(post, "updated_at") and post.updated_at:
                mod = post.updated_at.strftime("%Y-%m-%d")
            elif hasattr(post, "publish_date") and post.publish_date:
                mod = post.publish_date.strftime("%Y-%m-%d")
            add_entry(f"/blog/{post.slug}", changefreq="weekly", priority="0.7", lastmod=mod)

        # 9. Published Case Studies
        case_studies = db.query(CaseStudy).filter(CaseStudy.status == "published").all()
        for cs in case_studies:
            mod = cs.updated_at.strftime("%Y-%m-%d") if hasattr(cs, "updated_at") and cs.updated_at else None
            add_entry(f"/case-studies/{cs.slug}", changefreq="monthly", priority="0.7", lastmod=mod)

        # 10. Published Certifications
        certifications = db.query(Certification).filter(Certification.status == "published").all()
        for cert in certifications:
            slug = getattr(cert, "slug", None)
            if slug:
                mod = cert.updated_at.strftime("%Y-%m-%d") if hasattr(cert, "updated_at") and cert.updated_at else None
                add_entry(f"/certifications/{slug}", changefreq="monthly", priority="0.6", lastmod=mod)

        # 11. Published Dynamic CMS Pages (Excludes drafts)
        cms_pages = db.query(CMSPage).filter(CMSPage.status == PageStatus.PUBLISHED.value).all()
        for p in cms_pages:
            mod = p.updated_at.strftime("%Y-%m-%d") if hasattr(p, "updated_at") and p.updated_at else None
            add_entry(p.url_path, changefreq="weekly", priority="0.8", lastmod=mod)

        # XML Generation with proper XML entity escaping
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for e in entries:
            loc = saxutils.escape(e["loc"])
            xml_lines.append("  <url>")
            xml_lines.append(f"    <loc>{loc}</loc>")
            if "lastmod" in e and e["lastmod"]:
                xml_lines.append(f"    <lastmod>{saxutils.escape(e['lastmod'])}</lastmod>")
            if "changefreq" in e and e["changefreq"]:
                xml_lines.append(f"    <changefreq>{saxutils.escape(e['changefreq'])}</changefreq>")
            if "priority" in e and e["priority"]:
                xml_lines.append(f"    <priority>{saxutils.escape(e['priority'])}</priority>")
            xml_lines.append("  </url>")
        xml_lines.append("</urlset>")

        return "\n".join(xml_lines)


sitemap_service = SitemapService()
