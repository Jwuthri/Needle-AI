"""
ProductIntelligence model for storing competitive intelligence data from G2, TrustRadius, etc.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class ProductIntelligence(Base):
    """
    Competitive intelligence data scraped from G2, TrustRadius, Trustpilot, etc.
    Stores product metadata, alternatives, pricing, features, and company info.
    """
    __tablename__ = "product_intelligence"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)  # "g2", "trustradius", "trustpilot"
    
    # External IDs
    external_product_id = Column(String(100), nullable=True)  # G2's product_id, etc.
    external_company_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)  # Link to the product page
    
    # Product Info
    product_name = Column(String(255), nullable=True)
    product_logo = Column(String(500), nullable=True)
    product_description = Column(Text, nullable=True)
    what_is = Column(Text, nullable=True)  # Short description
    positioning = Column(Text, nullable=True)  # Competitive positioning statement
    
    # Rating Summary
    total_reviews = Column(Integer, nullable=True)
    average_rating = Column(Float, nullable=True)
    medal_image = Column(String(500), nullable=True)  # G2 badge
    
    # Company Info
    vendor_name = Column(String(255), nullable=True)
    company_location = Column(String(255), nullable=True)
    company_founded_year = Column(Integer, nullable=True)
    company_website = Column(String(500), nullable=True)
    product_website = Column(String(500), nullable=True)
    
    # Social Media
    twitter_url = Column(String(500), nullable=True)
    twitter_followers = Column(Integer, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    linkedin_employees = Column(Integer, nullable=True)
    
    # Categories (JSON array)
    categories = Column(JSON, nullable=True)  # [{name, link}, ...]
    primary_category = Column(String(255), nullable=True)
    parent_category = Column(String(255), nullable=True)
    
    # Alternatives & Comparisons (JSON arrays)
    alternatives = Column(JSON, nullable=True)  # [{name, link, rating, reviews}, ...]
    comparisons = Column(JSON, nullable=True)  # [{name, link, logo}, ...]
    
    # Features (JSON)
    features = Column(JSON, nullable=True)  # [{name, features: [{name, percentage, based_on}]}, ...]
    feature_summary = Column(JSON, nullable=True)  # Simplified feature list
    
    # Pricing (JSON array)
    pricing_plans = Column(JSON, nullable=True)  # [{plan_name, plan_price, plan_description, plan_features}, ...]
    
    # Media
    screenshots = Column(JSON, nullable=True)  # [url, ...]
    videos = Column(JSON, nullable=True)  # [url, ...]
    
    # Additional
    supported_languages = Column(String(500), nullable=True)
    services_offered = Column(Text, nullable=True)
    
    # Raw data for debugging/future use
    raw_data = Column(JSON, nullable=True)
    
    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="intelligence")

    # Indexes
    __table_args__ = (
        Index('idx_product_intelligence_company', 'company_id'),
        Index('idx_product_intelligence_source', 'source'),
        Index('idx_product_intelligence_company_source', 'company_id', 'source'),
    )

    def __repr__(self):
        return f"<ProductIntelligence(id={self.id}, company_id={self.company_id}, source={self.source})>"

    def get_top_alternatives(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top alternatives sorted by reviews."""
        if not self.alternatives:
            return []
        sorted_alts = sorted(
            self.alternatives, 
            key=lambda x: x.get("reviews", 0), 
            reverse=True
        )
        return sorted_alts[:limit]

    def get_pricing_tiers(self) -> List[str]:
        """Get list of pricing tier names."""
        if not self.pricing_plans:
            return []
        return [p.get("plan_name", "") for p in self.pricing_plans if p.get("plan_name")]

    def get_feature_scores(self) -> Dict[str, float]:
        """Get feature scores as a dict."""
        scores = {}
        if not self.features:
            return scores
        for category in self.features:
            for feature in category.get("features", []):
                if isinstance(feature, dict) and feature.get("name") and feature.get("percentage"):
                    scores[feature["name"]] = feature["percentage"]
        return scores

