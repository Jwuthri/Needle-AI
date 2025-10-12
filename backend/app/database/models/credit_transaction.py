"""
Credit transaction model for tracking purchases and usage.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class TransactionTypeEnum(str, enum.Enum):
    """Credit transaction types."""
    PURCHASE = "purchase"  # User bought credits
    DEDUCTION = "deduction"  # Credits spent on scraping
    REFUND = "refund"  # Credits refunded
    BONUS = "bonus"  # Free credits given


class CreditTransaction(Base):
    """Credit transaction history for auditing."""
    __tablename__ = "credit_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # References
    user_credit_id = Column(String, ForeignKey("user_credits.id"), nullable=False)
    scraping_job_id = Column(String, ForeignKey("scraping_jobs.id"), nullable=True)  # If related to scraping

    # Transaction details
    transaction_type = Column(SQLEnum(TransactionTypeEnum), nullable=False, index=True)
    amount = Column(Float, nullable=False)  # Positive for credits added, negative for deductions
    description = Column(Text, nullable=True)

    # Payment integration
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)

    # Balance snapshot
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user_credit = relationship("UserCredit", back_populates="transactions")
    scraping_job = relationship("ScrapingJob")

    # Indexes
    __table_args__ = (
        Index('idx_transactions_user_created', 'user_credit_id', 'created_at'),
        Index('idx_transactions_type', 'transaction_type', 'created_at'),
        Index('idx_transactions_stripe', 'stripe_payment_intent_id'),
    )

    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"

