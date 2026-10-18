from sqlalchemy import Column, String, Integer
from app.core.database import Base


class URLRedirect(Base):
    """
    Permanent (301) and temporary (302) URL redirect mapping table.
    Ensures that when a published page's slug changes, legacy URLs
    are preserved without SEO loss.
    """
    __tablename__ = "url_redirects"

    source_path = Column(String(500), unique=True, index=True, nullable=False)
    target_path = Column(String(500), nullable=False)
    status_code = Column(Integer, default=301, nullable=False)

    def __repr__(self) -> str:
        return f"<URLRedirect {self.source_path} -> {self.target_path} ({self.status_code})>"
