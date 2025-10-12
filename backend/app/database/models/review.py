"""
Review model for collected customer feedback.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class Review(Base):
    """Collected review/feedback from various sources."""
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # References
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    source_id = Column(String, ForeignKey("review_sources.id"), nullable=False)
    scraping_job_id = Column(String, ForeignKey("scraping_jobs.id"), nullable=True)  # Null for manual imports

    # Content
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)  # Link to original review

    # Analysis
    sentiment_score = Column(Float, nullable=True)  # -1.0 (negative) to 1.0 (positive)
    
    # Additional metadata (e.g., upvotes, platform-specific data)
    metadata = Column(JSON, default={}, nullable=False)

    # Vector database reference
    vector_id = Column(String, nullable=True, index=True)  # Pinecone vector ID

    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When sentiment analysis was done
    review_date = Column(DateTime, nullable=True)  # Original review timestamp if available

    # Relationships
    company = relationship("Company", back_populates="reviews")
    source = relationship("ReviewSource", back_populates="reviews")
    scraping_job = relationship("ScrapingJob", back_populates="reviews")

    # Indexes
    __table_args__ = (
        Index('idx_reviews_company_scraped', 'company_id', 'scraped_at'),
        Index('idx_reviews_sentiment', 'sentiment_score'),
        Index('idx_reviews_source', 'source_id', 'scraped_at'),
        Index('idx_reviews_job', 'scraping_job_id'),
        Index('idx_reviews_vector', 'vector_id'),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, company_id={self.company_id}, sentiment={self.sentiment_score})>"

