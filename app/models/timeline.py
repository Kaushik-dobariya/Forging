from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base


class TimelineMilestone(Base):
    """
    Chronological milestone entry for company history and corporate journey.
    """
    __tablename__ = "timeline_milestones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    year = Column(String(50), nullable=False)  # e.g., '1988', '1995', '2004', '2016', '2024'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String(500), nullable=True)
    supporting_info = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TimelineMilestone id={self.id} year='{self.year}' title='{self.title[:30]}'>"
