"""Add product_intelligence table for competitive data from G2, TrustRadius, etc.

Revision ID: 020_add_product_intelligence
Revises: 019_convert_enum_to_string
Create Date: 2024-11-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_intelligence",
        # Primary key and relationships
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        
        # External IDs
        sa.Column("external_product_id", sa.String(100), nullable=True),
        sa.Column("external_company_id", sa.String(100), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        
        # Product Info
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_logo", sa.String(500), nullable=True),
        sa.Column("product_description", sa.Text(), nullable=True),
        sa.Column("what_is", sa.Text(), nullable=True),
        sa.Column("positioning", sa.Text(), nullable=True),
        
        # Rating Summary
        sa.Column("total_reviews", sa.Integer(), nullable=True),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("medal_image", sa.String(500), nullable=True),
        
        # Company Info
        sa.Column("vendor_name", sa.String(255), nullable=True),
        sa.Column("company_location", sa.String(255), nullable=True),
        sa.Column("company_founded_year", sa.Integer(), nullable=True),
        sa.Column("company_website", sa.String(500), nullable=True),
        sa.Column("product_website", sa.String(500), nullable=True),
        
        # Social Media
        sa.Column("twitter_url", sa.String(500), nullable=True),
        sa.Column("twitter_followers", sa.Integer(), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("linkedin_employees", sa.Integer(), nullable=True),
        
        # Categories (JSON)
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("primary_category", sa.String(255), nullable=True),
        sa.Column("parent_category", sa.String(255), nullable=True),
        
        # Alternatives & Comparisons (JSON)
        sa.Column("alternatives", sa.JSON(), nullable=True),
        sa.Column("comparisons", sa.JSON(), nullable=True),
        
        # Features (JSON)
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("feature_summary", sa.JSON(), nullable=True),
        
        # Pricing (JSON)
        sa.Column("pricing_plans", sa.JSON(), nullable=True),
        
        # Media (JSON)
        sa.Column("screenshots", sa.JSON(), nullable=True),
        sa.Column("videos", sa.JSON(), nullable=True),
        
        # Additional
        sa.Column("supported_languages", sa.String(500), nullable=True),
        sa.Column("services_offered", sa.Text(), nullable=True),
        
        # Raw data
        sa.Column("raw_data", sa.JSON(), nullable=True),
        
        # Timestamps
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE"
        ),
    )
    
    # Create indexes
    op.create_index(
        "idx_product_intelligence_company",
        "product_intelligence",
        ["company_id"]
    )
    op.create_index(
        "idx_product_intelligence_source",
        "product_intelligence",
        ["source"]
    )
    op.create_index(
        "idx_product_intelligence_company_source",
        "product_intelligence",
        ["company_id", "source"]
    )


def downgrade() -> None:
    op.drop_index("idx_product_intelligence_company_source")
    op.drop_index("idx_product_intelligence_source")
    op.drop_index("idx_product_intelligence_company")
    op.drop_table("product_intelligence")

