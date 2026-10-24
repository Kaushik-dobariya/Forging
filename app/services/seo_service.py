import re
import json
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, urlunparse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.logging import logger
from app.models.setting import SiteSetting, SocialLink


def slugify(text: str) -> str:
    """Converts raw text into a clean, lowercase, URL-safe slug."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def strip_html(text: Optional[str]) -> str:
    """Removes HTML markup from content for clean meta descriptions."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class SEOService:
    """
    Unified SEO and Structured Data service for the Industrial Forging platform.
    Dynamically generates meta tags, canonical links, Open Graph, Twitter cards,
    and Schema.org JSON-LD structured data for all content types.
    """

    @staticmethod
    def ensure_unique_slug(
        db: Session,
        model_class: Any,
        base_text: str,
        current_id: Optional[Any] = None,
        preferred_slug: Optional[str] = None,
    ) -> str:
        """
        Generates a unique, lowercase slug for any model class, appending numerical suffixes if needed.
        """
        int_current_id = None
        if isinstance(current_id, int):
            int_current_id = current_id
        elif isinstance(current_id, str) and not preferred_slug:
            preferred_slug = current_id

        raw_slug = slugify(preferred_slug or base_text)
        if not raw_slug:
            raw_slug = "item"

        slug_candidate = raw_slug
        counter = 2

        while True:
            query = db.query(model_class).filter(model_class.slug == slug_candidate)
            if int_current_id is not None:
                query = query.filter(model_class.id != int_current_id)
            existing = query.first()
            if not existing:
                return slug_candidate
            slug_candidate = f"{raw_slug}-{counter}"
            counter += 1

    @staticmethod
    def build_canonical_url(path: str, base_url: Optional[str] = None) -> str:
        """
        Constructs a stable, lowercase canonical URL, stripping query parameters and trailing slashes.
        """
        # Handle swapped argument order (base_url, path)
        if base_url is not None and (path.startswith("http://") or path.startswith("https://")) and not (base_url.startswith("http://") or base_url.startswith("https://")):
            path, base_url = base_url, path

        domain = (base_url or settings.SITE_URL or "").rstrip("/")
        if not domain:
            domain = "http://localhost:8000"

        # Normalize path
        parsed = urlparse(path if path.startswith("/") else f"/{path}")
        clean_path = parsed.path.lower()
        if len(clean_path) > 1 and clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")

        return f"{domain}{clean_path}"


    def get_company_info(self, db: Optional[Session]) -> Dict[str, Any]:
        """Fetches dynamic company and website settings from database."""
        default_info = {
            "name": settings.APP_NAME or "FORGE Precision Engineering Ltd.",
            "url": settings.SITE_URL or "http://localhost:8000",
            "logo": f"{settings.SITE_URL}/static/images/logo.png",
            "phone": "+91 281 2345678",
            "email": "info@forgingcms.com",
            "address": {
                "street": "Plot 42, GIDC Industrial Estate, Phase II",
                "city": "Rajkot",
                "region": "Gujarat",
                "postal_code": "360002",
                "country": "IN",
            },
            "same_as": [
                "https://www.linkedin.com/company/forge-precision-engineering",
                "https://twitter.com/forging_cms",
                "https://www.youtube.com/@forging_cms",
            ],
        }

        if not db:
            return default_info

        try:
            settings_rows = db.query(SiteSetting).all()
            s_map = {s.key: s.value for s in settings_rows if s.value}

            if "general_company_name" in s_map:
                default_info["name"] = s_map["general_company_name"]
            elif "general_website_name" in s_map:
                default_info["name"] = s_map["general_website_name"]

            if "general_logo_url" in s_map:
                default_info["logo"] = s_map["general_logo_url"]

            if "contact_phone" in s_map:
                default_info["phone"] = s_map["contact_phone"]
            if "contact_email" in s_map:
                default_info["email"] = s_map["contact_email"]

            if "contact_address" in s_map:
                default_info["address"]["street"] = s_map["contact_address"]
            if "contact_city" in s_map:
                default_info["address"]["city"] = s_map["contact_city"]
            if "contact_state" in s_map:
                default_info["address"]["region"] = s_map["contact_state"]
            if "contact_postal_code" in s_map:
                default_info["address"]["postal_code"] = s_map["contact_postal_code"]
            if "contact_country" in s_map:
                default_info["address"]["country"] = s_map["contact_country"]

            social_links = db.query(SocialLink).filter(SocialLink.is_enabled == True).all()
            if social_links:
                default_info["same_as"] = [link.url for link in social_links if link.url]

        except Exception as exc:
            logger.warning(f"Error loading company info for SEO: {exc}")

        return default_info

    # --------------------------------------------------------------------------
    # SCHEMA.ORG JSON-LD BUILDERS
    # --------------------------------------------------------------------------

    def build_organization_schema(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates Organization JSON-LD."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        logo_url = info["logo"] if info["logo"].startswith("http") else f"{base_url}{info['logo']}"

        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": info["name"],
            "legalName": info["name"],
            "url": base_url,
            "logo": logo_url,
            "contactPoint": [
                {
                    "@type": "ContactPoint",
                    "telephone": info["phone"],
                    "contactType": "customer service",
                    "email": info["email"],
                    "areaServed": "Global",
                    "availableLanguage": ["English", "Hindi"],
                }
            ],
            "sameAs": info["same_as"],
        }

    def build_local_business_schema(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates LocalBusiness / ManufacturingBusiness JSON-LD."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        logo_url = info["logo"] if info["logo"].startswith("http") else f"{base_url}{info['logo']}"

        return {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "additionalType": "https://schema.org/AutomotiveBusiness",
            "name": info["name"],
            "image": logo_url,
            "url": base_url,
            "telephone": info["phone"],
            "email": info["email"],
            "priceRange": "$$$$",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": info["address"]["street"],
                "addressLocality": info["address"]["city"],
                "addressRegion": info["address"]["region"],
                "postalCode": info["address"]["postal_code"],
                "addressCountry": info["address"]["country"],
            },
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "opens": "08:00",
                    "closes": "19:00",
                }
            ],
        }

    def build_product_schema(self, product: Any, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates Schema.org Product JSON-LD dynamically from CMS Product data."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        cat_slug = product.category.slug if getattr(product, "category", None) else "all"
        product_url = f"{base_url}/products/{cat_slug}/{product.slug}"

        images = []
        if getattr(product, "featured_image", None):
            feat = product.featured_image
            images.append(feat if feat.startswith("http") else f"{base_url}{feat}")
        if hasattr(product, "images") and product.images:
            for img in product.images:
                url = img.image_url
                full_url = url if url.startswith("http") else f"{base_url}{url}"
                if full_url not in images:
                    images.append(full_url)

        desc = getattr(product, "short_description", None) or getattr(product, "meta_description", None) or getattr(product, "detailed_description", None) or product.name
        clean_desc = strip_html(desc)[:500]

        prod_id = getattr(product, "id", None)
        prod_slug = getattr(product, "slug", "product")
        sku_val = f"PRD-{prod_id:04d}" if prod_id else f"PRD-{prod_slug}"
        mpn_val = f"FORGE-{prod_slug.upper()}"

        quote_target = f"{base_url}/request-a-quote?product_id={prod_id}" if prod_id else f"{base_url}/request-a-quote?product={prod_slug}"

        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.name,
            "description": clean_desc,
            "url": product_url,
            "sku": sku_val,
            "mpn": mpn_val,
            "category": product.category.name if getattr(product, "category", None) else "Industrial Forgings",

            "manufacturer": {
                "@type": "Organization",
                "name": info["name"],
                "url": base_url,
            },
            "brand": {
                "@type": "Brand",
                "name": info["name"],
            },
            "offers": {
                "@type": "Offer",
                "priceCurrency": "USD",
                "price": "0.00",
                "priceValidUntil": "2030-12-31",
                "availability": "https://schema.org/InStock",
                "url": quote_target,
            },
        }

        if images:
            schema["image"] = images

        if getattr(product, "material", None):
            schema["material"] = product.material

        # Add technical specifications as additionalProperty
        if hasattr(product, "specifications") and product.specifications:
            props = []
            for spec in product.specifications:
                props.append({
                    "@type": "PropertyValue",
                    "name": spec.name,
                    "value": f"{spec.value} {spec.unit or ''}".strip(),
                })
            if props:
                schema["additionalProperty"] = props

        return schema

    def build_article_schema(self, post: Any, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates Schema.org Article / BlogPosting JSON-LD dynamically."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        post_url = f"{base_url}/blog/{post.slug}"

        image_url = None
        if getattr(post, "featured_image", None):
            fi = post.featured_image
            image_url = fi if fi.startswith("http") else f"{base_url}{fi}"
        elif getattr(post, "og_image", None):
            oi = post.og_image
            image_url = oi if oi.startswith("http") else f"{base_url}{oi}"

        pub_date = ""
        if hasattr(post, "publish_date") and post.publish_date:
            pub_date = post.publish_date.isoformat()
        elif hasattr(post, "created_at") and post.created_at:
            pub_date = post.created_at.isoformat()

        mod_date = pub_date
        if hasattr(post, "updated_at") and post.updated_at:
            mod_date = post.updated_at.isoformat()

        headline = post.seo_title or post.title
        desc = strip_html(post.meta_description or post.excerpt or post.content)[:300]

        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": post_url,
            },
            "headline": headline,
            "description": desc,
            "datePublished": pub_date,
            "dateModified": mod_date,
            "author": {
                "@type": "Person",
                "name": getattr(post, "author", None) or info["name"],
            },
            "publisher": {
                "@type": "Organization",
                "name": info["name"],
                "logo": {
                    "@type": "ImageObject",
                    "url": info["logo"] if info["logo"].startswith("http") else f"{base_url}{info['logo']}",
                },
            },
            "articleSection": getattr(post, "category", "Forging Technology"),
        }

        if image_url:
            schema["image"] = image_url

        return schema

    def build_case_study_schema(self, case_study: Any, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates Schema.org Article / TechArticle for engineering case studies."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        url = f"{base_url}/case-studies/{case_study.slug}"

        image_url = None
        if getattr(case_study, "featured_image", None):
            fi = case_study.featured_image
            image_url = fi if fi.startswith("http") else f"{base_url}{fi}"

        headline = case_study.seo_title or case_study.title
        desc = strip_html(case_study.meta_description or case_study.client_challenge)[:300]

        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": headline,
            "description": desc,
            "url": url,
            "about": getattr(case_study, "client_industry", "Industrial Forging"),
            "author": {
                "@type": "Organization",
                "name": info["name"],
            },
            "publisher": {
                "@type": "Organization",
                "name": info["name"],
            },
        }
        if image_url:
            schema["image"] = image_url

        return schema

    build_tech_article_schema = build_case_study_schema

    def build_equipment_schema(self, equipment: Any, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generates Schema.org Product / IndividualProduct for equipment fleet."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"
        slug = getattr(equipment, "slug", None) or slugify(equipment.name)
        url = f"{base_url}/machinery/{slug}"

        image_url = None
        if getattr(equipment, "image", None):
            im = equipment.image
            image_url = im if im.startswith("http") else f"{base_url}{im}"

        desc = strip_html(getattr(equipment, "meta_description", None) or equipment.description or equipment.specifications or equipment.name)[:300]

        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": equipment.name,
            "description": desc,
            "url": url,
            "category": getattr(equipment, "category", "Heavy Forging Machinery"),
            "manufacturer": {
                "@type": "Organization",
                "name": getattr(equipment, "manufacturer", None) or info["name"],
            },
        }
        if image_url:
            schema["image"] = image_url
        if getattr(equipment, "capacity", None):
            schema["additionalProperty"] = [
                {
                    "@type": "PropertyValue",
                    "name": "Capacity",
                    "value": equipment.capacity,
                }
            ]

        return schema

    def build_breadcrumb_schema(self, breadcrumbs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generates Schema.org BreadcrumbList JSON-LD."""
        base_url = settings.SITE_URL or "http://localhost:8000"
        items = []

        for idx, crumb in enumerate(breadcrumbs, start=1):
            url = crumb.get("url", "/")
            full_url = url if url.startswith("http") else f"{base_url}{url}"
            items.append({
                "@type": "ListItem",
                "position": idx,
                "name": crumb.get("name", "Page"),
                "item": full_url,
            })

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        }

    def build_faq_schema(self, faqs: List[Any]) -> Optional[Dict[str, Any]]:
        """Generates Schema.org FAQPage JSON-LD."""
        if not faqs:
            return None

        main_entities = []
        for f in faqs:
            q = getattr(f, "question", None) or (f.get("question") if isinstance(f, dict) else None)
            a = getattr(f, "answer", None) or (f.get("answer") if isinstance(f, dict) else None)
            if q and a:
                main_entities.append({
                    "@type": "Question",
                    "name": strip_html(q),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": strip_html(a),
                    },
                })

        if not main_entities:
            return None

        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": main_entities,
        }

    def build_webpage_schema(
        self,
        title: str,
        description: str,
        url: str,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Generates WebPage JSON-LD."""
        info = self.get_company_info(db)
        base_url = settings.SITE_URL or "http://localhost:8000"

        return {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": url,
            "isPartOf": {
                "@type": "WebSite",
                "name": info["name"],
                "url": base_url,
            },
        }

    def generate_json_ld(self, schema_type: str, **kwargs) -> Dict[str, Any]:
        """
        Unified dispatch generator for Schema.org JSON-LD structured data.
        Supported types: 'organization', 'local_business', 'product', 'article',
        'tech_article', 'equipment', 'breadcrumb', 'faq', 'webpage'.
        """
        st = schema_type.lower().replace("-", "_")
        db = kwargs.get("db")
        if st in ("organization", "org"):
            return self.build_organization_schema(db)
        elif st in ("local_business", "localbusiness"):
            return self.build_local_business_schema(db)
        elif st in ("product", "products"):
            return self.build_product_schema(kwargs.get("entity") or kwargs.get("product"), db)
        elif st in ("article", "blog", "post", "blogposting"):
            return self.build_article_schema(kwargs.get("entity") or kwargs.get("post"), db)
        elif st in ("tech_article", "case_study", "case"):
            return self.build_tech_article_schema(kwargs.get("entity") or kwargs.get("case_study"), db)
        elif st in ("equipment", "machinery"):
            return self.build_equipment_schema(kwargs.get("entity") or kwargs.get("equipment"), db)
        elif st in ("breadcrumb", "breadcrumbs", "breadcrumblist"):
            items = kwargs.get("breadcrumb_items") or kwargs.get("breadcrumbs") or []
            normalized = []
            for item in items:
                if isinstance(item, (tuple, list)) and len(item) >= 2:
                    normalized.append({"name": item[0], "url": item[1]})
                elif isinstance(item, dict):
                    normalized.append(item)
            return self.build_breadcrumb_schema(normalized)
        elif st in ("faq", "faqpage"):
            items = kwargs.get("faq_items") or kwargs.get("faqs") or []
            return self.build_faq_schema(items) or {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
        elif st in ("webpage", "page"):
            title = kwargs.get("page_title") or kwargs.get("title") or "Page"
            desc = kwargs.get("page_description") or kwargs.get("description") or ""
            url = kwargs.get("canonical_url") or kwargs.get("url") or "/"
            return self.build_webpage_schema(title, desc, url, db)
        else:
            return {"@context": "https://schema.org", "@type": "WebPage", "name": schema_type}

    # --------------------------------------------------------------------------
    # UNIFIED SEO CONTEXT BUILDER
    # --------------------------------------------------------------------------


    def get_seo_context(
        self,
        path: str,
        entity: Optional[Any] = None,
        entity_type: Optional[str] = None,
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        custom_canonical: Optional[str] = None,
        og_type: str = "website",
        og_image: Optional[str] = None,
        breadcrumbs: Optional[List[Dict[str, str]]] = None,
        noindex: bool = False,
        faqs: Optional[List[Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Builds complete, production-ready SEO metadata dictionary ready for Jinja2 templates.
        Supports automatic extraction for:
        - pages (CMSPage)
        - products (Product)
        - capabilities (Capability)
        - industries (Industry)
        - materials (Material)
        - equipment (Equipment)
        - blogs (BlogPost)
        - case studies (CaseStudy)
        - certifications (Certification)
        """
        info = self.get_company_info(db)
        site_name = info["name"]
        base_url = settings.SITE_URL or "http://localhost:8000"

        # 1. Canonical URL calculation
        canonical_url = custom_canonical or self.build_canonical_url(path, base_url)

        # 2. Extract Title and Description
        title = custom_title
        description = custom_description
        image_url = og_image

        schemas_list: List[Dict[str, Any]] = []

        # If admin area, force noindex
        if path.startswith("/admin") or path.startswith("/api"):
            noindex = True

        if entity:
            if entity_type == "product" or entity.__class__.__name__ == "Product":
                og_type = "product"
                title = entity.meta_title or f"{entity.name} | Precision Forged Components"
                description = entity.meta_description or entity.short_description or entity.detailed_description
                if getattr(entity, "featured_image", None):
                    image_url = entity.featured_image
                schemas_list.append(self.build_product_schema(entity, db))

            elif entity_type == "blog" or entity.__class__.__name__ == "BlogPost":
                og_type = "article"
                title = entity.seo_title or f"{entity.title} | {site_name}"
                description = entity.meta_description or entity.excerpt or entity.content
                if getattr(entity, "featured_image", None):
                    image_url = entity.featured_image
                elif getattr(entity, "og_image", None):
                    image_url = entity.og_image
                schemas_list.append(self.build_article_schema(entity, db))

            elif entity_type == "case_study" or entity.__class__.__name__ == "CaseStudy":
                og_type = "article"
                title = entity.seo_title or f"{entity.title} | Engineering Case Study"
                description = entity.meta_description or entity.client_challenge or entity.engineering_approach
                if getattr(entity, "featured_image", None):
                    image_url = entity.featured_image
                schemas_list.append(self.build_case_study_schema(entity, db))

            elif entity_type == "capability" or entity.__class__.__name__ == "Capability":
                title = entity.meta_title or f"{entity.title} | Manufacturing Services"
                description = entity.meta_description or entity.short_description or entity.detailed_description
                if getattr(entity, "hero_image", None):
                    image_url = entity.hero_image

            elif entity_type == "industry" or entity.__class__.__name__ == "Industry":
                title = entity.meta_title or f"{entity.name} Forged Components & Engineering"
                description = entity.meta_description or entity.short_description or entity.detailed_description
                if getattr(entity, "hero_image", None):
                    image_url = entity.hero_image

            elif entity_type == "material" or entity.__class__.__name__ == "Material":
                title = entity.meta_title or f"{entity.name} ({getattr(entity, 'grade', '')}) Forging Grade"
                description = entity.meta_description or entity.description or entity.applications
                if getattr(entity, "image", None):
                    image_url = entity.image

            elif entity_type == "equipment" or entity.__class__.__name__ == "Equipment":
                title = getattr(entity, "meta_title", None) or f"{entity.name} | Heavy Machinery Fleet"
                description = getattr(entity, "meta_description", None) or entity.description or entity.specifications
                if getattr(entity, "image", None):
                    image_url = entity.image
                schemas_list.append(self.build_equipment_schema(entity, db))

            elif entity_type == "certification" or entity.__class__.__name__ == "Certification":
                title = getattr(entity, "meta_title", None) or f"{entity.certificate_name} Accreditation | Quality Standards"
                description = getattr(entity, "meta_description", None) or entity.description or f"Official quality certification: {entity.certificate_name}"
                if getattr(entity, "certificate_image", None):
                    image_url = entity.certificate_image

            elif entity_type == "page" or entity.__class__.__name__ == "CMSPage":
                title = entity.meta_title or entity.title
                description = entity.meta_description or entity.content
                if getattr(entity, "og_image", None):
                    image_url = entity.og_image
                elif getattr(entity, "featured_image", None):
                    image_url = entity.featured_image
                if getattr(entity, "canonical_url", None):
                    canonical_url = entity.canonical_url
                if not entity.is_published:
                    noindex = True

        # Fallback title & description
        if not title:
            title = f"{site_name} | High-Precision Closed & Open Die Forgings"
        if not description:
            description = (
                "Leading manufacturer of high-precision closed-die and open-die forgings, "
                "rolled rings, and CNC-machined components for aerospace, automotive, oil & gas, and heavy industry."
            )

        clean_title = strip_html(title)
        clean_description = strip_html(description)[:160]

        # Format full image URL
        if not image_url:
            image_url = info["logo"]
        if image_url and not image_url.startswith("http"):
            image_url = f"{base_url}{image_url}"

        # 3. Add base schemas: Organization & WebPage & Breadcrumbs
        if not noindex:
            if path in ["/", ""]:
                schemas_list.append(self.build_organization_schema(db))
                schemas_list.append(self.build_local_business_schema(db))
            else:
                schemas_list.append(self.build_webpage_schema(clean_title, clean_description, canonical_url, db))

            if breadcrumbs:
                schemas_list.append(self.build_breadcrumb_schema(breadcrumbs))

            if faqs:
                faq_schema = self.build_faq_schema(faqs)
                if faq_schema:
                    schemas_list.append(faq_schema)

        # 4. Serialize JSON-LD
        schema_json = ""
        if schemas_list:
            if len(schemas_list) == 1:
                schema_json = json.dumps(schemas_list[0], indent=2)
            else:
                graph_schema = {
                    "@context": "https://schema.org",
                    "@graph": schemas_list,
                }
                schema_json = json.dumps(graph_schema, indent=2)

        robots_directive = "noindex, nofollow" if noindex else "index, follow"

        return {
            "title": clean_title,
            "meta_description": clean_description,
            "canonical_url": canonical_url,
            "robots": robots_directive,
            "og_title": clean_title,
            "og_description": clean_description,
            "og_type": og_type,
            "og_url": canonical_url,
            "og_image": image_url,
            "og_site_name": site_name,
            "twitter_card": "summary_large_image",
            "twitter_title": clean_title,
            "twitter_description": clean_description,
            "twitter_image": image_url,
            "schema_json": schema_json,
            "breadcrumbs": breadcrumbs or [],
        }


seo_service = SEOService()
