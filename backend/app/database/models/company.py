"""
Company model for product review analysis.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class Company(Base):
    """Company/Product being analyzed for reviews and feedback."""
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)  # e.g., "gorgias.com"
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Ownership
    created_by = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="companies")
    reviews = relationship("Review", back_populates="company", cascade="all, delete-orphan")
    scraping_jobs = relationship("ScrapingJob", back_populates="company", cascade="all, delete-orphan")
    data_imports = relationship("DataImport", back_populates="company", cascade="all, delete-orphan")
    intelligence = relationship("ProductIntelligence", back_populates="company", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_companies_user_created', 'created_by', 'created_at'),
        Index('idx_companies_domain', 'domain'),
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name}, domain={self.domain})>"

