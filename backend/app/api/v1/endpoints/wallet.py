"""
Wallet and transaction endpoints
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_compliance_requirements,
    get_payment_processor,
    get_user_location,
)
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.wallet import (
    DepositRequest,
    PaymentIntentResponse,
    TransactionListResponse,
    TransactionResponse,
    WalletResponse,
    WithdrawalRequest,
)
from app.services.wallet_service import WalletService

router = APIRouter()


@router.get("/", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user wallet information"""
    wallet_service = WalletService(db)
    wallet = await wallet_service.get_or_create_wallet(current_user.id)
    return WalletResponse.from_orm(wallet)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user transaction history"""
    wallet_service = WalletService(db)
    transactions, total = await wallet_service.get_transactions(
        user_id=current_user.id, page=page, limit=limit
    )

    pages = (total + limit - 1) // limit

    return TransactionListResponse(
        items=[TransactionResponse.from_orm(t) for t in transactions],
        total=total,
        page=page,
        size=limit,
        pages=pages,
    )


@router.post("/deposit", response_model=PaymentIntentResponse)
async def create_deposit_intent(
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    location: dict = Depends(get_user_location),
    payment_processor: str = Depends(get_payment_processor),
    compliance_requirements: dict = Depends(get_compliance_requirements),
):
    """Create a deposit payment intent"""
    # Check compliance requirements
    if not location.get("compliance_status") == "allowed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deposits not allowed from this location",
        )

    # Check deposit limits
    daily_limit = compliance_requirements.get("deposit_limits", {}).get("daily", 1000)
    if deposit_data.amount > daily_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deposit amount exceeds daily limit of ${daily_limit}",
        )

    wallet_service = WalletService(db)

    try:
        # Route to appropriate payment processor based on location
        result = await wallet_service.create_deposit_intent(
            user_id=current_user.id,
            amount=deposit_data.amount,
            payment_processor=payment_processor,
        )

        # Determine currency based on location
        currency = "USD" if location.get("country") == "US" else "MXN"

        return PaymentIntentResponse(
            client_secret=result.get("client_secret"),
            payment_intent_id=result.get("payment_intent_id"),
            preference_id=result.get("preference_id"),
            init_point=result.get("init_point"),
            sandbox_init_point=result.get("sandbox_init_point"),
            payment_processor=payment_processor,
            amount=deposit_data.amount,
            currency=currency,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create deposit intent: {str(e)}",
        )


@router.post("/deposit/confirm")
async def confirm_deposit(
    payment_intent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a completed deposit"""
    wallet_service = WalletService(db)

    try:
        transaction = await wallet_service.confirm_deposit(payment_intent_id)
        return {
            "message": "Deposit confirmed successfully",
            "transaction_id": transaction.id,
            "amount": transaction.amount,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to confirm deposit: {str(e)}",
        )


@router.post("/withdraw", response_model=TransactionResponse)
async def request_withdrawal(
    withdrawal_data: WithdrawalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a withdrawal"""
    wallet_service = WalletService(db)

    try:
        transaction = await wallet_service.request_withdrawal(
            user_id=current_user.id, amount=withdrawal_data.amount
        )
        return TransactionResponse.from_orm(transaction)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process withdrawal request: {str(e)}",
        )


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's available and locked balance"""
    wallet_service = WalletService(db)
    available, locked = await wallet_service.get_wallet_balance(current_user.id)

    return {
        "available_balance": available,
        "locked_balance": locked,
        "total_balance": available + locked,
    }
