"""
ProductIntelligence API models for competitive intelligence data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Nested Models ---

class Alternative(BaseModel):
    """Alternative/competitor product."""
    name: str
    link: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None


class Comparison(BaseModel):
    """Product comparison."""
    name: str
    link: Optional[str] = None
    logo: Optional[str] = None


class Category(BaseModel):
    """Product category."""
    name: str
    link: Optional[str] = None


class PricingPlan(BaseModel):
    """Pricing plan info."""
    plan_name: str
    plan_price: Optional[str] = None
    plan_description: Optional[str] = None
    plan_features: Optional[List[str]] = None


class FeatureScore(BaseModel):
    """Individual feature score."""
    name: str
    percentage: Optional[float] = None
    based_on_number_of_reviews: Optional[int] = None
    content: Optional[str] = None


class FeatureCategory(BaseModel):
    """Feature category with scores."""
    name: str
    features: List[FeatureScore] = []


# --- Request/Response Models ---

class ProductIntelligenceCreate(BaseModel):
    """Request model for creating product intelligence."""
    company_id: str
    source: str = Field(..., description="Source: g2, trustradius, trustpilot")
    
    # External IDs
    external_product_id: Optional[str] = None
    external_company_id: Optional[str] = None
    external_url: Optional[str] = None
    
    # Product Info
    product_name: Optional[str] = None
    product_logo: Optional[str] = None
    product_description: Optional[str] = None
    what_is: Optional[str] = None
    positioning: Optional[str] = None
    
    # Rating Summary
    total_reviews: Optional[int] = None
    average_rating: Optional[float] = None
    medal_image: Optional[str] = None
    
    # Company Info
    vendor_name: Optional[str] = None
    company_location: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_website: Optional[str] = None
    product_website: Optional[str] = None
    
    # Social Media
    twitter_url: Optional[str] = None
    twitter_followers: Optional[int] = None
    linkedin_url: Optional[str] = None
    linkedin_employees: Optional[int] = None
    
    # Categories
    categories: Optional[List[Dict[str, Any]]] = None
    primary_category: Optional[str] = None
    parent_category: Optional[str] = None
    
    # Alternatives & Comparisons
    alternatives: Optional[List[Dict[str, Any]]] = None
    comparisons: Optional[List[Dict[str, Any]]] = None
    
    # Features
    features: Optional[List[Dict[str, Any]]] = None
    feature_summary: Optional[List[Dict[str, Any]]] = None
    
    # Pricing
    pricing_plans: Optional[List[Dict[str, Any]]] = None
    
    # Media
    screenshots: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    
    # Additional
    supported_languages: Optional[str] = None
    services_offered: Optional[str] = None
    
    # Raw data
    raw_data: Optional[Dict[str, Any]] = None


class ProductIntelligenceResponse(BaseModel):
    """Response model for product intelligence."""
    id: str
    company_id: str
    source: str
    
    # External IDs
    external_product_id: Optional[str] = None
    external_company_id: Optional[str] = None
    external_url: Optional[str] = None
    
    # Product Info
    product_name: Optional[str] = None
    product_logo: Optional[str] = None
    product_description: Optional[str] = None
    what_is: Optional[str] = None
    positioning: Optional[str] = None
    
    # Rating Summary
    total_reviews: Optional[int] = None
    average_rating: Optional[float] = None
    medal_image: Optional[str] = None
    
    # Company Info
    vendor_name: Optional[str] = None
    company_location: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_website: Optional[str] = None
    product_website: Optional[str] = None
    
    # Social Media
    twitter_url: Optional[str] = None
    twitter_followers: Optional[int] = None
    linkedin_url: Optional[str] = None
    linkedin_employees: Optional[int] = None
    
    # Categories
    categories: Optional[List[Category]] = None
    primary_category: Optional[str] = None
    parent_category: Optional[str] = None
    
    # Alternatives & Comparisons
    alternatives: Optional[List[Alternative]] = None
    comparisons: Optional[List[Comparison]] = None
    
    # Features
    features: Optional[List[FeatureCategory]] = None
    feature_summary: Optional[List[Dict[str, Any]]] = None
    
    # Pricing
    pricing_plans: Optional[List[PricingPlan]] = None
    
    # Media
    screenshots: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    
    # Additional
    supported_languages: Optional[str] = None
    services_offered: Optional[str] = None
    
    # Timestamps
    scraped_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductIntelligenceSummary(BaseModel):
    """Summarized intelligence for dashboard display."""
    id: str
    source: str
    product_name: Optional[str] = None
    product_logo: Optional[str] = None
    average_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    alternatives_count: int = 0
    pricing_tiers: List[str] = []
    top_features: List[str] = []
    scraped_at: datetime

    class Config:
        from_attributes = True


class CompetitorSummary(BaseModel):
    """Summary of a competitor from alternatives data."""
    name: str
    rating: Optional[float] = None
    reviews: Optional[int] = None
    link: Optional[str] = None
    source: str  # Where we got this info


class CompetitiveAnalysis(BaseModel):
    """Aggregated competitive analysis for a company."""
    company_id: str
    company_name: str
    
    # Own product stats
    average_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    
    # Competitors
    top_competitors: List[CompetitorSummary] = []
    
    # Feature gaps (features where competitors score higher)
    feature_gaps: List[Dict[str, Any]] = []
    
    # Pricing comparison
    pricing_tiers: List[str] = []
    
    # Categories
    categories: List[str] = []
    
    # Sources
    sources: List[str] = []
    last_updated: Optional[datetime] = None

