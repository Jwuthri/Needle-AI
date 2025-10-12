"""
CreditTransaction repository for transaction history.
"""

from typing import List

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.credit_transaction import CreditTransaction, TransactionTypeEnum
from app.utils.logging import get_logger

logger = get_logger("credit_transaction_repository")


class CreditTransactionRepository:
    """Repository for CreditTransaction model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_credit_id: str,
        transaction_type: TransactionTypeEnum,
        amount: float,
        balance_before: float,
        balance_after: float,
        description: str = None,
        scraping_job_id: str = None,
        stripe_payment_intent_id: str = None
    ) -> CreditTransaction:
        """Create a new credit transaction."""
        transaction = CreditTransaction(
            user_credit_id=user_credit_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            scraping_job_id=scraping_job_id,
            stripe_payment_intent_id=stripe_payment_intent_id
        )
        db.add(transaction)
        await db.flush()
        await db.refresh(transaction)
        logger.info(f"Created transaction: {transaction.id} - {transaction_type} - {amount}")
        return transaction

    @staticmethod
    async def list_user_transactions(
        db: AsyncSession,
        user_credit_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditTransaction]:
        """List transactions for a user credit account."""
        result = await db.execute(
            select(CreditTransaction)
            .filter(CreditTransaction.user_credit_id == user_credit_id)
            .order_by(desc(CreditTransaction.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_by_type(
        db: AsyncSession,
        user_credit_id: str,
        transaction_type: TransactionTypeEnum,
        limit: int = 50
    ) -> List[CreditTransaction]:
        """List transactions by type."""
        result = await db.execute(
            select(CreditTransaction)
            .filter(
                CreditTransaction.user_credit_id == user_credit_id,
                CreditTransaction.transaction_type == transaction_type
            )
            .order_by(desc(CreditTransaction.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

