"""
User credit model for payment tracking.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from ..base import Base


class UserCredit(Base):
    """User credit balance for review scraping (Stripe integration)."""
    __tablename__ = "user_credits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # User reference (one-to-one relationship)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Credit balances
    credits_available = Column(Float, default=0.0, nullable=False)  # Current available credits
    total_purchased = Column(Float, default=0.0, nullable=False)  # Lifetime purchased credits
    total_spent = Column(Float, default=0.0, nullable=False)  # Lifetime spent credits

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_purchase_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="credit_account", uselist=False)
    transactions = relationship("CreditTransaction", back_populates="user_credit", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_credits_stripe', 'stripe_customer_id'),
    )

    def __repr__(self):
        return f"<UserCredit(user_id={self.user_id}, available={self.credits_available})>"

