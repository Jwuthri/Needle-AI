"""
Review source model for configurable data sources.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class SourceTypeEnum(str, enum.Enum):
    """Available review source types."""
    REDDIT = "reddit"
    TWITTER = "twitter"
    CUSTOM_CSV = "custom_csv"
    CUSTOM_JSON = "custom_json"


class ReviewSource(Base):
    """Configurable review sources (Reddit, Twitter, custom imports)."""
    __tablename__ = "review_sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, index=True)
    source_type = Column(SQLEnum(SourceTypeEnum), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Configuration (e.g., API credentials, scraper settings)
    config = Column(JSON, default={}, nullable=False)

    # Pricing
    cost_per_review = Column(Float, default=0.01, nullable=False)  # Cost in credits per review

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    scraping_jobs = relationship("ScrapingJob", back_populates="source")
    reviews = relationship("Review", back_populates="source")

    # Indexes
    __table_args__ = (
        Index('idx_sources_type_active', 'source_type', 'is_active'),
    )

    def __repr__(self):
        return f"<ReviewSource(id={self.id}, name={self.name}, type={self.source_type})>"

