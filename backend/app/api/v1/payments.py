"""
Payment API endpoints for credit purchases.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.services.payment_service import PaymentService
from app.utils.logging import get_logger

logger = get_logger("payments_api")

router = APIRouter()


class CheckoutRequest(BaseModel):
    """Request for creating a checkout session."""
    package_name: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Response with checkout session details."""
    session_id: str
    checkout_url: str


class BalanceResponse(BaseModel):
    """User credit balance response."""
    credits_available: float
    total_purchased: float
    total_spent: float


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    data: CheckoutRequest,
    current_user: ClerkUser = Depends(get_current_user)
) -> CheckoutResponse:
    """
    Create a Stripe checkout session for credit purchase.
    
    Available packages: starter, professional, enterprise
    """
    try:
        payment_service = PaymentService()
        
        result = await payment_service.create_checkout_session(
            user_id=current_user.id,
            package_name=data.package_name,
            success_url=data.success_url,
            cancel_url=data.cancel_url
        )
        
        logger.info(f"Created checkout session for user {current_user.id}")
        
        return CheckoutResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    This endpoint is called by Stripe to notify about payment events.
    """
    try:
        # Get raw body and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        payment_service = PaymentService()
        result = await payment_service.handle_webhook(payload, signature)
        
        logger.info(f"Processed webhook event: {result}")
        
        return {"received": True, "result": result}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook error: {str(e)}"
        )


@router.get("/credits", response_model=BalanceResponse)
async def get_credit_balance(
    current_user: ClerkUser = Depends(get_current_user)
) -> BalanceResponse:
    """Get current user's credit balance."""
    try:
        payment_service = PaymentService()
        balance = await payment_service.get_customer_balance(current_user.id)
        
        return BalanceResponse(**balance)
        
    except Exception as e:
        logger.error(f"Error getting credit balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credit balance: {str(e)}"
        )


@router.get("/packages")
async def list_credit_packages():
    """List available credit packages."""
    try:
        payment_service = PaymentService()
        packages = payment_service.list_available_packages()
        
        return {"packages": packages}
        
    except Exception as e:
        logger.error(f"Error listing packages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list packages: {str(e)}"
        )

