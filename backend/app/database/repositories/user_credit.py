"""
UserCredit repository for managing user credit balances.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.user_credit import UserCredit
from app.utils.logging import get_logger

logger = get_logger("user_credit_repository")


class UserCreditRepository:
    """Repository for UserCredit model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        stripe_customer_id: Optional[str] = None
    ) -> UserCredit:
        """Create a new user credit account."""
        credit_account = UserCredit(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id
        )
        db.add(credit_account)
        await db.flush()
        await db.refresh(credit_account)
        logger.info(f"Created credit account for user: {user_id}")
        return credit_account

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[UserCredit]:
        """Get credit account by user ID."""
        result = await db.execute(select(UserCredit).filter(UserCredit.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_stripe_customer_id(
        db: AsyncSession,
        stripe_customer_id: str
    ) -> Optional[UserCredit]:
        """Get credit account by Stripe customer ID."""
        result = await db.execute(
            select(UserCredit).filter(UserCredit.stripe_customer_id == stripe_customer_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        user_id: str,
        stripe_customer_id: Optional[str] = None
    ) -> UserCredit:
        """Get existing credit account or create new one."""
        credit_account = await UserCreditRepository.get_by_user_id(db, user_id)
        if not credit_account:
            credit_account = await UserCreditRepository.create(db, user_id, stripe_customer_id)
        return credit_account

    @staticmethod
    async def add_credits(
        db: AsyncSession,
        user_id: str,
        amount: float
    ) -> Optional[UserCredit]:
        """Add credits to user account."""
        credit_account = await UserCreditRepository.get_by_user_id(db, user_id)
        if not credit_account:
            return None

        credit_account.credits_available += amount
        credit_account.total_purchased += amount
        credit_account.last_purchase_at = datetime.utcnow()

        await db.flush()
        await db.refresh(credit_account)
        logger.info(f"Added {amount} credits to user {user_id}")
        return credit_account

    @staticmethod
    async def deduct_credits(
        db: AsyncSession,
        user_id: str,
        amount: float
    ) -> Optional[UserCredit]:
        """Deduct credits from user account."""
        credit_account = await UserCreditRepository.get_by_user_id(db, user_id)
        if not credit_account:
            return None

        if credit_account.credits_available < amount:
            logger.warning(f"Insufficient credits for user {user_id}: {credit_account.credits_available} < {amount}")
            return None

        credit_account.credits_available -= amount
        credit_account.total_spent += amount

        await db.flush()
        await db.refresh(credit_account)
        logger.info(f"Deducted {amount} credits from user {user_id}")
        return credit_account

    @staticmethod
    async def has_sufficient_credits(
        db: AsyncSession,
        user_id: str,
        required_amount: float
    ) -> bool:
        """Check if user has sufficient credits."""
        credit_account = await UserCreditRepository.get_by_user_id(db, user_id)
        if not credit_account:
            return False
        return credit_account.credits_available >= required_amount

    @staticmethod
    async def set_stripe_customer_id(
        db: AsyncSession,
        user_id: str,
        stripe_customer_id: str
    ) -> Optional[UserCredit]:
        """Set Stripe customer ID."""
        credit_account = await UserCreditRepository.get_by_user_id(db, user_id)
        if not credit_account:
            return None

        credit_account.stripe_customer_id = stripe_customer_id
        await db.flush()
        await db.refresh(credit_account)
        return credit_account

