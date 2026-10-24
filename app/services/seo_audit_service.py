import json
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.product import Product, ProductCategory
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.material import Material
from app.models.infrastructure import Equipment
from app.models.quality import Certification
from app.models.blog import BlogPost, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.page import CMSPage, PageStatus
from app.models.menu import MenuItem
from app.models.media import MediaAsset
from app.services.seo_service import seo_service


class SEOAuditService:
    """
    Automated SEO Health & Validation Engine.
    Executes systematic audits for:
      - Duplicate titles
      - Missing meta descriptions
      - Missing canonical URLs
      - Duplicate slugs
      - Missing image alt text
      - Broken internal links
      - Invalid structured data (JSON-LD) generation
    """

    def run_full_audit(self, db: Session, base_url: str = "https://forgingcms.com") -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        # 1. Check Duplicate Titles & Missing Descriptions
        title_map = defaultdict(list)
        entity_counts = {"total_entities": 0, "entities_with_issues": 0}

        def record_entity(entity_type: str, item_id: int, title: Optional[str], desc: Optional[str], slug: Optional[str], url: str):
            entity_counts["total_entities"] += 1
            has_issue = False

            eff_title = (title or "").strip()
            if not eff_title:
                issues.append({
                    "severity": "critical",
                    "category": "Missing Title",
                    "entity_type": entity_type,
                    "entity_id": item_id,
                    "url": url,
                    "message": f"{entity_type} #{item_id} has no title or meta_title defined.",
                })
                has_issue = True
            else:
                title_map[eff_title.lower()].append({
                    "entity_type": entity_type,
                    "id": item_id,
                    "title": eff_title,
                    "url": url,
                })

            eff_desc = (desc or "").strip()
            if not eff_desc:
                issues.append({
                    "severity": "warning",
                    "category": "Missing Meta Description",
                    "entity_type": entity_type,
                    "entity_id": item_id,
                    "url": url,
                    "message": f"{entity_type} #{item_id} has empty meta_description. Search engines will generate fallback snippets.",
                })
                has_issue = True
            elif len(eff_desc) < 50:
                issues.append({
                    "severity": "info",
                    "category": "Short Meta Description",
                    "entity_type": entity_type,
                    "entity_id": item_id,
                    "url": url,
                    "message": f"{entity_type} #{item_id} meta_description is very short ({len(eff_desc)} chars). Recommended: 120-160.",
                })

            if not slug:
                issues.append({
                    "severity": "critical",
                    "category": "Missing Slug",
                    "entity_type": entity_type,
                    "entity_id": item_id,
                    "url": url,
                    "message": f"{entity_type} #{item_id} is missing an indexable URL slug.",
                })
                has_issue = True

            # Canonical check
            canonical = seo_service.build_canonical_url(base_url, url)
            if not canonical or not canonical.startswith("http"):
                issues.append({
                    "severity": "critical",
                    "category": "Invalid Canonical",
                    "entity_type": entity_type,
                    "entity_id": item_id,
                    "url": url,
                    "message": f"Could not construct a valid canonical URL for {url}.",
                })
                has_issue = True

            if has_issue:
                entity_counts["entities_with_issues"] += 1

        # Scan Products
        products = db.query(Product).filter(Product.status == "published").all()
        for p in products:
            record_entity("Product", p.id, p.meta_title or p.name, p.meta_description or p.short_description, p.slug, f"/products/{p.slug}")

        # Scan Product Categories
        categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).all()
        for c in categories:
            record_entity("Product Category", c.id, c.meta_title or c.name, c.meta_description, c.slug, f"/products?category={c.slug}")

        # Scan Capabilities
        capabilities = db.query(Capability).filter(Capability.status == "published").all()
        for cap in capabilities:
            record_entity("Capability", cap.id, cap.meta_title or cap.title, cap.meta_description or cap.short_description, cap.slug, f"/capabilities/{cap.slug}")

        # Scan Industries
        industries = db.query(Industry).filter(Industry.status == "published").all()
        for ind in industries:
            record_entity("Industry", ind.id, ind.meta_title or ind.name, ind.meta_description or ind.short_description, ind.slug, f"/industries/{ind.slug}")

        # Scan Materials
        materials = db.query(Material).filter(Material.status == "published").all()
        for m in materials:
            record_entity("Material", m.id, m.meta_title or m.name, m.meta_description or m.description, m.slug, f"/materials/{m.slug}")

        # Scan Equipment
        equipments = db.query(Equipment).filter(Equipment.status == "published").all()
        for eq in equipments:
            eq_slug = eq.slug or str(eq.id)
            record_entity("Equipment", eq.id, eq.meta_title or eq.name, eq.meta_description or eq.description, eq_slug, f"/machinery/{eq_slug}")

        # Scan Certifications
        certs = db.query(Certification).filter(Certification.status == "published").all()
        for cr in certs:
            cr_name = getattr(cr, "certificate_name", None) or getattr(cr, "name", f"Certification {cr.id}")
            cr_slug = cr.slug or str(cr.id)
            record_entity("Certification", cr.id, cr.meta_title or cr_name, cr.meta_description or cr.description, cr_slug, f"/certifications/{cr_slug}")

        # Scan Blogs
        posts = db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.PUBLISHED.value).all()
        for post in posts:
            record_entity("Blog Post", post.id, post.seo_title or post.title, post.meta_description or post.excerpt, post.slug, f"/blog/{post.slug}")

        # Scan Case Studies
        cases = db.query(CaseStudy).filter(CaseStudy.status == "published").all()
        for cs in cases:
            record_entity("Case Study", cs.id, cs.seo_title or cs.title, cs.meta_description or cs.client_challenge, cs.slug, f"/case-studies/{cs.slug}")


        # Scan CMS Pages
        pages = db.query(CMSPage).filter(CMSPage.status == PageStatus.PUBLISHED.value).all()
        for pg in pages:
            record_entity("CMS Page", pg.id, pg.meta_title or pg.title, pg.meta_description, pg.slug, f"/{pg.slug}")

        # Check for Duplicate Titles across different entities
        for title_str, occurrences in title_map.items():
            if len(occurrences) > 1:
                urls = ", ".join(o["url"] for o in occurrences)
                issues.append({
                    "severity": "critical",
                    "category": "Duplicate Title",
                    "entity_type": "Multiple",
                    "entity_id": 0,
                    "url": occurrences[0]["url"],
                    "message": f"Duplicate page title '{title_str}' shared by {len(occurrences)} URLs: {urls}",
                })

        # 2. Check for Duplicate Slugs within each entity collection
        slug_check_collections = [
            ("Product", [p.slug for p in products if p.slug]),
            ("Capability", [c.slug for c in capabilities if c.slug]),
            ("Industry", [i.slug for i in industries if i.slug]),
            ("Material", [m.slug for m in materials if m.slug]),
            ("Equipment", [e.slug for e in equipments if e.slug]),
            ("Certification", [cr.slug for cr in certs if cr.slug]),
            ("Blog Post", [b.slug for b in posts if b.slug]),
            ("Case Study", [cs.slug for cs in cases if cs.slug]),
            ("CMS Page", [p.slug for p in pages if p.slug]),
        ]
        for cname, slugs in slug_check_collections:
            seen_slugs = set()
            for s in slugs:
                s_lower = s.lower()
                if s_lower in seen_slugs:
                    issues.append({
                        "severity": "critical",
                        "category": "Duplicate Slug",
                        "entity_type": cname,
                        "entity_id": 0,
                        "url": f"/{s_lower}",
                        "message": f"Duplicate slug '{s_lower}' detected within {cname} collection.",
                    })
                seen_slugs.add(s_lower)

        # 3. Check Image Alt Text in Media Assets
        media_assets = db.query(MediaAsset).all()
        missing_alt_count = 0
        for m in media_assets:
            if not m.alt_text or not m.alt_text.strip():
                missing_alt_count += 1
                issues.append({
                    "severity": "warning",
                    "category": "Missing Image Alt Text",
                    "entity_type": "MediaAsset",
                    "entity_id": m.id,
                    "url": m.file_path,
                    "message": f"Media asset '{m.seo_filename or m.filename}' is missing descriptive accessibility alt text.",
                })

        # 4. Check Internal Links from Navigation Menus
        menu_items = db.query(MenuItem).filter(MenuItem.is_enabled == True).all()
        for item in menu_items:
            url = item.url or ""
            if url.startswith("/") and not url.startswith("//"):
                clean_url = url.split("?")[0].rstrip("/") or "/"
                # Simple pattern verification
                known_prefixes = [
                    "/", "/about", "/contact", "/products", "/capabilities",
                    "/industries", "/materials", "/infrastructure", "/machinery",
                    "/certifications", "/quality", "/blog", "/case-studies",
                    "/downloads", "/faq", "/rfq", "/quote"
                ]
                # If path starts with known prefix or matches a CMS page, it's valid
                matches_prefix = any(clean_url == p or clean_url.startswith(f"{p}/") for p in known_prefixes)
                matches_page = any(clean_url == f"/{pg.slug}" for pg in pages)
                if not (matches_prefix or matches_page):
                    issues.append({
                        "severity": "warning",
                        "category": "Broken Internal Link",
                        "entity_type": "MenuItem",
                        "entity_id": item.id,
                        "url": url,
                        "message": f"Menu item '{item.title}' points to '{url}', which does not match a standard route or published CMS page.",
                    })

        # 5. Validate Structured Data (JSON-LD) Generation
        schemas_to_test = [
            ("Organization", lambda: seo_service.generate_json_ld("organization", base_url=base_url)),
            ("LocalBusiness", lambda: seo_service.generate_json_ld("local_business", base_url=base_url)),
            ("WebPage", lambda: seo_service.generate_json_ld("webpage", base_url=base_url, page_title="Test Home", page_description="Test Description", canonical_url=base_url)),
            ("BreadcrumbList", lambda: seo_service.generate_json_ld("breadcrumb", base_url=base_url, breadcrumb_items=[("Home", "/"), ("Products", "/products")])),
            ("FAQPage", lambda: seo_service.generate_json_ld("faq", faq_items=[{"question": "Q1?", "answer": "A1"}])),
        ]
        if products:
            schemas_to_test.append(
                ("Product", lambda: seo_service.generate_json_ld("product", base_url=base_url, entity=products[0]))
            )
        if posts:
            schemas_to_test.append(
                ("Article", lambda: seo_service.generate_json_ld("article", base_url=base_url, entity=posts[0]))
            )
        if cases:
            schemas_to_test.append(
                ("TechArticle", lambda: seo_service.generate_json_ld("tech_article", base_url=base_url, entity=cases[0]))
            )

        schema_failures = 0
        for sname, gen_fn in schemas_to_test:
            try:
                schema_dict = gen_fn()
                if not schema_dict.get("@context") or not schema_dict.get("@type"):
                    raise ValueError("Missing @context or @type")
                # Verify JSON serializability
                json_str = json.dumps(schema_dict)
                if len(json_str) < 10:
                    raise ValueError("Generated JSON-LD string is too short")
            except Exception as exc:
                schema_failures += 1
                issues.append({
                    "severity": "critical",
                    "category": "Invalid Structured Data",
                    "entity_type": sname,
                    "entity_id": 0,
                    "url": "/",
                    "message": f"Failed generating valid JSON-LD schema for {sname}: {exc}",
                })

        # Calculate Overall SEO Score
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        # Baseline score: 100 - (critical * 10) - (warning * 2) - (info * 0.5)
        raw_score = 100 - (critical_count * 10) - (warning_count * 2) - (info_count * 0.5)
        score = max(0, min(100, int(round(raw_score))))

        return {
            "score": score,
            "total_entities_checked": entity_counts["total_entities"],
            "total_issues": len(issues),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "issues": issues,
            "structured_data_validated": len(schemas_to_test) - schema_failures,
        }


seo_audit_service = SEOAuditService()
