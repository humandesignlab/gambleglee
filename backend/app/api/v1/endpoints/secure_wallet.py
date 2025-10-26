"""
Secure wallet endpoints with comprehensive security measures
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from decimal import Decimal
import time

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.dependencies import (
    get_user_location,
    get_payment_processor,
    get_compliance_requirements,
)
from app.core.security_audit import SecurityAudit
from app.models.user import User
from app.schemas.wallet import (
    WalletResponse,
    TransactionResponse,
    DepositRequest,
    WithdrawalRequest,
    PaymentIntentResponse,
    TransactionListResponse,
)
from app.services.secure_wallet_service import SecureWalletService
from app.core.exceptions import SecurityError

router = APIRouter()

# Rate limiting storage (in production, use Redis)
_rate_limit_storage = {}


def _check_rate_limit(
    user_id: int, endpoint: str, limit: int = 10, window: int = 60
) -> bool:
    """Simple rate limiting (in production, use Redis with proper distributed rate limiting)"""
    current_time = time.time()
    key = f"{user_id}:{endpoint}"

    if key not in _rate_limit_storage:
        _rate_limit_storage[key] = []

    # Clean old entries
    _rate_limit_storage[key] = [
        timestamp
        for timestamp in _rate_limit_storage[key]
        if current_time - timestamp < window
    ]

    # Check if limit exceeded
    if len(_rate_limit_storage[key]) >= limit:
        return False

    # Add current request
    _rate_limit_storage[key].append(current_time)
    return True


@router.get("/", response_model=WalletResponse)
async def get_wallet(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user wallet information with security checks"""
    # Rate limiting
    if not _check_rate_limit(current_user.id, "get_wallet", limit=30, window=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    # Security audit
    security_audit = SecurityAudit(db)
    alerts = await security_audit.detect_suspicious_activity(current_user.id)

    if alerts:
        for alert in alerts:
            await security_audit.log_security_event(
                alert["type"], current_user.id, alert, alert["severity"]
            )

    wallet_service = SecureWalletService(db)
    wallet = await wallet_service.get_or_create_wallet(current_user.id, current_user.id)

    return WalletResponse.from_orm(wallet)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user transaction history with security checks"""
    # Rate limiting
    if not _check_rate_limit(current_user.id, "get_transactions", limit=20, window=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    wallet_service = SecureWalletService(db)
    transactions, total = await wallet_service.get_transactions(
        user_id=current_user.id, current_user_id=current_user.id, page=page, limit=limit
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
    request: Request,
    deposit_data: DepositRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    location: dict = Depends(get_user_location),
    payment_processor: str = Depends(get_payment_processor),
    compliance_requirements: dict = Depends(get_compliance_requirements),
):
    """Create a deposit payment intent with comprehensive security checks"""
    # Rate limiting (stricter for deposits)
    if not _check_rate_limit(current_user.id, "create_deposit", limit=5, window=300):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Deposit rate limit exceeded. Please wait before trying again.",
        )

    # Security checks
    security_audit = SecurityAudit(db)

    # Check for suspicious activity
    alerts = await security_audit.detect_suspicious_activity(current_user.id)
    if any(alert["severity"] == "critical" for alert in alerts):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily restricted due to suspicious activity",
        )

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

    # Check velocity limits
    amount_decimal = Decimal(str(deposit_data.amount))
    from app.models.wallet import TransactionType

    velocity_ok = await security_audit.check_velocity_limits(
        current_user.id, amount_decimal, TransactionType.DEPOSIT
    )

    if not velocity_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Deposit velocity limit exceeded. Please wait before trying again.",
        )

    wallet_service = SecureWalletService(db)

    try:
        # Route to appropriate payment processor based on location
        result = await wallet_service.create_deposit_intent(
            user_id=current_user.id,
            amount=deposit_data.amount,
            payment_processor=payment_processor,
        )

        # Log security event
        await security_audit.log_security_event(
            "deposit_intent_created",
            current_user.id,
            {
                "amount": deposit_data.amount,
                "payment_processor": payment_processor,
                "location": location.get("country"),
                "ip_address": request.client.host if request.client else "unknown",
            },
            "low",
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

    except SecurityError as e:
        await security_audit.log_security_event(
            "deposit_security_error",
            current_user.id,
            {"error": str(e), "amount": deposit_data.amount},
            "high",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Security check failed"
        )
    except Exception as e:
        await security_audit.log_security_event(
            "deposit_error",
            current_user.id,
            {"error": str(e), "amount": deposit_data.amount},
            "medium",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create deposit intent: {str(e)}",
        )


@router.post("/withdraw", response_model=TransactionResponse)
async def request_withdrawal(
    request: Request,
    withdrawal_data: WithdrawalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    location: dict = Depends(get_user_location),
    compliance_requirements: dict = Depends(get_compliance_requirements),
):
    """Request a withdrawal with comprehensive security checks"""
    # Rate limiting (stricter for withdrawals)
    if not _check_rate_limit(
        current_user.id, "request_withdrawal", limit=3, window=3600
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Withdrawal rate limit exceeded. Please wait before trying again.",
        )

    # Security checks
    security_audit = SecurityAudit(db)

    # Check for suspicious activity
    alerts = await security_audit.detect_suspicious_activity(current_user.id)
    if any(alert["severity"] in ["critical", "high"] for alert in alerts):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily restricted due to suspicious activity",
        )

    # Check compliance requirements
    if not location.get("compliance_status") == "allowed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Withdrawals not allowed from this location",
        )

    # Check withdrawal limits
    daily_limit = compliance_requirements.get("withdrawal_limits", {}).get(
        "daily", 5000
    )
    if withdrawal_data.amount > daily_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Withdrawal amount exceeds daily limit of ${daily_limit}",
        )

    # Check velocity limits
    amount_decimal = Decimal(str(withdrawal_data.amount))
    from app.models.wallet import TransactionType

    velocity_ok = await security_audit.check_velocity_limits(
        current_user.id, amount_decimal, TransactionType.WITHDRAWAL
    )

    if not velocity_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Withdrawal velocity limit exceeded. Please wait before trying again.",
        )

    wallet_service = SecureWalletService(db)

    try:
        transaction = await wallet_service.request_withdrawal(
            user_id=current_user.id,
            amount=withdrawal_data.amount,
            description="Withdrawal request",
            current_user_id=current_user.id,
        )

        # Log security event
        await security_audit.log_security_event(
            "withdrawal_requested",
            current_user.id,
            {
                "amount": withdrawal_data.amount,
                "ip_address": request.client.host if request.client else "unknown",
            },
            "medium",
        )

        return TransactionResponse.from_orm(transaction)

    except SecurityError as e:
        await security_audit.log_security_event(
            "withdrawal_security_error",
            current_user.id,
            {"error": str(e), "amount": withdrawal_data.amount},
            "high",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Security check failed"
        )
    except Exception as e:
        await security_audit.log_security_event(
            "withdrawal_error",
            current_user.id,
            {"error": str(e), "amount": withdrawal_data.amount},
            "medium",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process withdrawal request: {str(e)}",
        )


@router.get("/balance")
async def get_balance(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's available and locked balance with security checks"""
    # Rate limiting
    if not _check_rate_limit(current_user.id, "get_balance", limit=60, window=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    wallet_service = SecureWalletService(db)
    available, locked = await wallet_service.get_wallet_balance(
        current_user.id, current_user.id
    )

    return {
        "available_balance": float(available),
        "locked_balance": float(locked),
        "total_balance": float(available + locked),
    }


@router.get("/audit")
async def audit_wallet(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit wallet integrity (admin function)"""
    # Rate limiting
    if not _check_rate_limit(current_user.id, "audit_wallet", limit=5, window=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    security_audit = SecurityAudit(db)
    audit_result = await security_audit.audit_wallet_integrity(current_user.id)

    return audit_result
