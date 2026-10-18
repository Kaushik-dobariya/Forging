import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, Enum
from app.core.database import Base


class BlogCategory(str, enum.Enum):
    FORGING_TECHNOLOGY = "Forging Technology"
    INDUSTRY_INSIGHTS = "Industry Insights"
    ENGINEERING = "Engineering"
    MANUFACTURING = "Manufacturing"
    QUALITY = "Quality"
    COMPANY_NEWS = "Company News"
    CASE_STUDIES = "Case Studies"


class BlogPostStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"


class BlogPost(Base):
    """
    Blog post model for industrial forging articles, technology updates, and case studies.
    """
    __tablename__ = "blog_posts"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    featured_image = Column(String(500), nullable=True)
    author = Column(String(100), default="Forging Engineering Team", nullable=False)
    category = Column(String(100), default=BlogCategory.FORGING_TECHNOLOGY.value, nullable=False)
    excerpt = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(255), nullable=True)
    publish_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), default=BlogPostStatus.DRAFT.value, nullable=False)

    # SEO & Metadata
    seo_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    canonical_url = Column(String(500), nullable=True)
    og_image = Column(String(500), nullable=True)
    schema_config = Column(Text, nullable=True)  # Optional custom JSON schema overrides
    reading_time_minutes = Column(Integer, default=5, nullable=False)

    def __init__(self, **kwargs):
        if "published_at" in kwargs and "publish_date" not in kwargs:
            kwargs["publish_date"] = kwargs.pop("published_at")
        super().__init__(**kwargs)
        if self.content:
            word_count = len(str(self.content).split())
            calc_time = max(1, round(word_count / 200))
            if "reading_time_minutes" not in kwargs or kwargs.get("reading_time_minutes") == 5:
                self.reading_time_minutes = calc_time

    @property
    def published_at(self):
        return self.publish_date

    @published_at.setter
    def published_at(self, value):
        self.publish_date = value

    def is_visible_publicly(self) -> bool:
        """Determines if the article should be visible on the public website."""
        if self.status != BlogPostStatus.PUBLISHED.value:
            return False
        now = datetime.now(timezone.utc)
        pub_date = self.publish_date
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        return pub_date <= now

    def generate_schema_ld(self, base_url: str = "") -> dict:
        """Generates Schema.org TechArticle JSON-LD structured data."""
        base = base_url.rstrip("/")
        pub_iso = self.publish_date.isoformat() if self.publish_date else ""
        category_name = self.category.value if hasattr(self.category, "value") else str(self.category)
        return {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": self.title,
            "description": self.excerpt or self.meta_description or self.title,
            "url": f"{base}/blog/{self.slug}",
            "image": [self.og_image or self.featured_image] if (self.og_image or self.featured_image) else [],
            "datePublished": pub_iso,
            "dateModified": self.updated_at.isoformat() if self.updated_at else pub_iso,
            "author": {
                "@type": "Person",
                "name": self.author or "Forging Engineering Specialist",
            },
            "publisher": {
                "@type": "Organization",
                "name": "Precision Forging Plant & Heavy Engineering",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{base}/static/images/brand-logo.svg",
                },
            },
            "articleSection": category_name,
            "inLanguage": "en-US",
        }

    def __repr__(self) -> str:
        return f"<BlogPost id={self.id} slug='{self.slug}' status='{self.status}'>"

