"""
Stripe payment service for credit purchases.
"""

from typing import Any, Dict, Optional

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

from app.config import get_settings
from app.database.models.credit_transaction import TransactionTypeEnum
from app.database.repositories import UserCreditRepository, CreditTransactionRepository
from app.database.session import get_async_session
from app.exceptions import ConfigurationError, ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger("payment_service")


class PaymentService:
    """
    Stripe payment service for credit purchases.
    
    Features:
    - Create checkout sessions
    - Handle webhooks
    - Manage customer accounts
    - Credit balance management
    """

    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        
        # Only initialize Stripe if available
        if STRIPE_AVAILABLE:
            self._initialize_stripe()
        else:
            logger.warning("Stripe package not installed. Paid features will not be available.")

    def _initialize_stripe(self):
        """Initialize Stripe with API key."""
        if not STRIPE_AVAILABLE:
            raise ConfigurationError("Stripe package not installed. Install with: pip install stripe")
            
        secret_key = self.settings.get_secret("stripe_secret_key")
        if not secret_key:
            raise ConfigurationError("Stripe secret key not configured")

        stripe.api_key = secret_key
        logger.info("Stripe payment service initialized")

    async def create_checkout_session(
        self,
        user_id: str,
        package_name: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, str]:
        """
        Create a Stripe checkout session for credit purchase.
        
        Args:
            user_id: User ID
            package_name: Credit package name (starter, professional, enterprise)
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancellation
            
        Returns:
            Dict with session_id and checkout_url
        """
        try:
            # Get package details
            packages = self.settings.credit_packages
            if package_name not in packages:
                raise ValueError(f"Invalid package: {package_name}")

            amount_usd = packages[package_name]
            credits = amount_usd * 100  # $1 = 100 credits

            # Get or create Stripe customer
            async with get_async_session() as session:
                credit_account = await UserCreditRepository.get_or_create(
                    session,
                    user_id
                )
                
                stripe_customer_id = credit_account.stripe_customer_id
                
                if not stripe_customer_id:
                    # Create Stripe customer
                    customer = stripe.Customer.create(
                        metadata={"user_id": user_id}
                    )
                    stripe_customer_id = customer.id
                    
                    # Update credit account
                    await UserCreditRepository.set_stripe_customer_id(
                        session,
                        user_id,
                        stripe_customer_id
                    )
                    await session.commit()

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': self.settings.stripe_currency,
                        'product_data': {
                            'name': f'{package_name.capitalize()} Credit Package',
                            'description': f'{credits} credits for review analysis',
                        },
                        'unit_amount': amount_usd * 100,  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'package_name': package_name,
                    'credits': str(credits)
                }
            )

            logger.info(f"Created checkout session for user {user_id}: {checkout_session.id}")

            return {
                "session_id": checkout_session.id,
                "checkout_url": checkout_session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise ExternalServiceError(f"Payment session creation failed: {e}", service="stripe")
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            Result dictionary
        """
        webhook_secret = self.settings.get_secret("stripe_webhook_secret")
        if not webhook_secret:
            raise ConfigurationError("Stripe webhook secret not configured")

        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )

            # Handle different event types
            event_type = event['type']
            
            if event_type == 'checkout.session.completed':
                return await self._handle_checkout_completed(event['data']['object'])
            elif event_type == 'payment_intent.succeeded':
                return await self._handle_payment_succeeded(event['data']['object'])
            elif event_type == 'payment_intent.payment_failed':
                return await self._handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return {"handled": False, "event_type": event_type}

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ExternalServiceError("Invalid webhook signature", service="stripe")
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise

    async def _handle_checkout_completed(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful checkout session completion."""
        try:
            user_id = session['metadata']['user_id']
            package_name = session['metadata']['package_name']
            credits = int(session['metadata']['credits'])
            payment_intent_id = session.get('payment_intent')

            logger.info(f"Checkout completed for user {user_id}: {credits} credits")

            async with get_async_session() as db_session:
                # Get credit account
                credit_account = await UserCreditRepository.get_by_user_id(db_session, user_id)
                if not credit_account:
                    logger.error(f"Credit account not found for user {user_id}")
                    return {"handled": False, "error": "Credit account not found"}

                balance_before = credit_account.credits_available

                # Add credits
                await UserCreditRepository.add_credits(db_session, user_id, credits)

                # Record transaction
                await CreditTransactionRepository.create(
                    db_session,
                    user_credit_id=credit_account.id,
                    transaction_type=TransactionTypeEnum.PURCHASE,
                    amount=credits,
                    balance_before=balance_before,
                    balance_after=balance_before + credits,
                    description=f"Credit purchase: {package_name} package",
                    stripe_payment_intent_id=payment_intent_id
                )

                await db_session.commit()

            logger.info(f"Added {credits} credits to user {user_id}")

            return {
                "handled": True,
                "user_id": user_id,
                "credits_added": credits
            }

        except Exception as e:
            logger.error(f"Error handling checkout completed: {e}")
            raise

    async def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment intent."""
        logger.info(f"Payment succeeded: {payment_intent['id']}")
        return {"handled": True, "payment_intent_id": payment_intent['id']}

    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment intent."""
        logger.warning(f"Payment failed: {payment_intent['id']}")
        return {"handled": True, "payment_intent_id": payment_intent['id'], "status": "failed"}

    async def get_customer_balance(self, user_id: str) -> Dict[str, float]:
        """
        Get user's credit balance.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with balance information
        """
        async with get_async_session() as session:
            credit_account = await UserCreditRepository.get_by_user_id(session, user_id)
            
            logger.info(f"Getting balance for user {user_id}")
            
            if not credit_account:
                logger.warning(f"No credit account found for user {user_id}")
                return {
                    "credits_available": 0.0,
                    "total_purchased": 0.0,
                    "total_spent": 0.0
                }

            logger.info(f"User {user_id} balance: {credit_account.credits_available}")
            
            return {
                "credits_available": credit_account.credits_available,
                "total_purchased": credit_account.total_purchased,
                "total_spent": credit_account.total_spent
            }

    async def add_free_credits(self, user_id: str, amount: float) -> Dict[str, Any]:
        """
        Add free credits to user account (for testing/promotional purposes).
        
        Args:
            user_id: User ID
            amount: Amount of credits to add
            
        Returns:
            Dict with new balance and confirmation
        """
        async with get_async_session() as session:
            # Get or create credit account
            credit_account = await UserCreditRepository.get_or_create(session, user_id)
            balance_before = credit_account.credits_available
            
            logger.info(f"Adding {amount} free credits to user {user_id}. Balance before: {balance_before}")
            
            # Add credits
            updated_account = await UserCreditRepository.add_credits(session, user_id, amount)
            
            if not updated_account:
                logger.error(f"Failed to add credits to user {user_id}")
                raise Exception("Failed to update credit balance")
            
            logger.info(f"Credits after update: {updated_account.credits_available}")
            
            # Record transaction
            await CreditTransactionRepository.create(
                session,
                user_credit_id=credit_account.id,
                transaction_type=TransactionTypeEnum.PURCHASE,
                amount=amount,
                balance_before=balance_before,
                balance_after=updated_account.credits_available,
                description=f"Free credits (promotional)",
                stripe_payment_intent_id=None
            )
            
            await session.commit()
            
            # Refresh to get final state
            await session.refresh(updated_account)
            
            final_balance = updated_account.credits_available
            logger.info(f"Added {amount} free credits to user {user_id}. Final balance: {final_balance}")
            
            return {
                "credits_available": final_balance,
                "amount_added": amount,
                "message": f"Successfully added {amount} free credits"
            }

    def list_available_packages(self) -> Dict[str, Dict[str, Any]]:
        """List all available credit packages."""
        packages = {}
        
        for name, amount_usd in self.settings.credit_packages.items():
            credits = amount_usd * 100  # $1 = 100 credits
            
            packages[name] = {
                "name": name.capitalize(),
                "price_usd": amount_usd,
                "credits": credits,
                "price_per_credit": amount_usd / credits if credits > 0 else 0
            }

        return packages

    async def health_check(self) -> bool:
        """Check if Stripe service is healthy."""
        try:
            # Test API connection by retrieving account
            account = stripe.Account.retrieve()
            return bool(account.id)
        except Exception as e:
            logger.error(f"Stripe health check failed: {e}")
            return False

