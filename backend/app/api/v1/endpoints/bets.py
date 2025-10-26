"""
Comprehensive betting API endpoints for GambleGlee with extensive edge case handling
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BettingError, InsufficientFundsError, ValidationError
from app.core.rate_limiter import RateLimitException, rate_limiter
from app.core.security import get_current_active_user
from app.models.betting import Bet, BetOutcome, BetParticipant, BetStatus, BetType
from app.models.user import User
from app.services.betting_service import BettingService

logger = structlog.get_logger(__name__)

router = APIRouter()

# === PYDANTIC SCHEMAS ===


class BetCreateRequest(BaseModel):
    """Request to create a new bet"""

    title: str = Field(..., min_length=1, max_length=255, description="Bet title")
    description: Optional[str] = Field(
        None, max_length=1000, description="Bet description"
    )
    bet_type: BetType = Field(..., description="Type of bet")
    amount: float = Field(..., gt=0, le=10000, description="Bet amount (max $10,000)")
    acceptor_id: Optional[int] = Field(None, description="Specific user to accept bet")
    event_id: Optional[int] = Field(None, description="Associated event ID")
    event_type: Optional[str] = Field(None, description="Type of associated event")
    expires_in_hours: int = Field(
        24, ge=1, le=168, description="Hours until bet expires (max 7 days)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator("amount")
    def validate_amount(cls, v):
        if v < 1.0:
            raise ValueError("Minimum bet amount is $1.00")
        if v > 10000.0:
            raise ValueError("Maximum bet amount is $10,000.00")
        return v


class BetAcceptRequest(BaseModel):
    """Request to accept a bet"""

    bet_id: int = Field(..., description="ID of bet to accept")


class BetResolveRequest(BaseModel):
    """Request to resolve a bet"""

    bet_id: int = Field(..., description="ID of bet to resolve")
    outcome: BetOutcome = Field(..., description="Bet outcome")
    resolution_data: Optional[Dict[str, Any]] = Field(
        None, description="Resolution data"
    )
    resolution_method: str = Field("manual", description="Resolution method")


class BetCancelRequest(BaseModel):
    """Request to cancel a bet"""

    bet_id: int = Field(..., description="ID of bet to cancel")
    reason: str = Field(
        ..., min_length=1, max_length=500, description="Cancellation reason"
    )


class BetResponse(BaseModel):
    """Response for bet data"""

    id: int
    uuid: str
    title: str
    description: Optional[str]
    bet_type: str
    status: str
    outcome: str
    amount: float
    commission_amount: float
    total_pot: float
    winner_payout: float
    created_at: datetime
    accepted_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    resolved_at: Optional[datetime]
    expires_at: Optional[datetime]
    creator_id: int
    participants: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]


class BetListResponse(BaseModel):
    """Response for bet list"""

    items: List[BetResponse]
    total: int
    page: int
    size: int
    pages: int


class BetStatisticsResponse(BaseModel):
    """Response for bet statistics"""

    status_counts: Dict[str, int]
    total_bet_amount: float
    total_winnings: float
    net_profit: float


# === API ENDPOINTS ===


@router.post("/", response_model=BetResponse)
@rate_limiter(key="create_bet", rate="10/5minute")
async def create_bet(
    bet_data: BetCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Create a new bet with comprehensive validation"""
    try:
        betting_service = BettingService(db)

        # Convert amount to Decimal for precision
        amount = Decimal(str(bet_data.amount))

        bet = await betting_service.create_bet(
            creator_id=current_user.id,
            title=bet_data.title,
            description=bet_data.description,
            bet_type=bet_data.bet_type,
            amount=amount,
            acceptor_id=bet_data.acceptor_id,
            event_id=bet_data.event_id,
            event_type=bet_data.event_type,
            expires_in_hours=bet_data.expires_in_hours,
            metadata=bet_data.metadata,
        )

        # Get bet with participants for response
        bet_with_participants = await betting_service.get_bet(bet.id)

        return BetResponse(
            id=bet_with_participants.id,
            uuid=bet_with_participants.uuid,
            title=bet_with_participants.title,
            description=bet_with_participants.description,
            bet_type=bet_with_participants.bet_type.value,
            status=bet_with_participants.status.value,
            outcome=bet_with_participants.outcome.value,
            amount=float(bet_with_participants.amount),
            commission_amount=float(bet_with_participants.commission_amount),
            total_pot=float(bet_with_participants.total_pot),
            winner_payout=float(bet_with_participants.winner_payout),
            created_at=bet_with_participants.created_at,
            accepted_at=bet_with_participants.accepted_at,
            started_at=bet_with_participants.started_at,
            completed_at=bet_with_participants.completed_at,
            resolved_at=bet_with_participants.resolved_at,
            expires_at=bet_with_participants.expires_at,
            creator_id=bet_with_participants.created_by,
            participants=[
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "stake_amount": float(p.stake_amount),
                    "potential_winnings": (
                        float(p.potential_winnings) if p.potential_winnings else None
                    ),
                    "actual_winnings": (
                        float(p.actual_winnings) if p.actual_winnings else None
                    ),
                    "is_active": p.is_active,
                }
                for p in bet_with_participants.participants
            ],
            metadata=bet_with_participants.metadata,
        )

    except RateLimitException as e:
        logger.warning("Rate limit exceeded for bet creation", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to create bet", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bet",
        )


@router.post("/accept", response_model=BetResponse)
@rate_limiter(key="accept_bet", rate="20/5minute")
async def accept_bet(
    accept_data: BetAcceptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a bet with comprehensive validation"""
    try:
        betting_service = BettingService(db)

        bet = await betting_service.accept_bet(
            bet_id=accept_data.bet_id, acceptor_id=current_user.id
        )

        # Get bet with participants for response
        bet_with_participants = await betting_service.get_bet(bet.id)

        return BetResponse(
            id=bet_with_participants.id,
            uuid=bet_with_participants.uuid,
            title=bet_with_participants.title,
            description=bet_with_participants.description,
            bet_type=bet_with_participants.bet_type.value,
            status=bet_with_participants.status.value,
            outcome=bet_with_participants.outcome.value,
            amount=float(bet_with_participants.amount),
            commission_amount=float(bet_with_participants.commission_amount),
            total_pot=float(bet_with_participants.total_pot),
            winner_payout=float(bet_with_participants.winner_payout),
            created_at=bet_with_participants.created_at,
            accepted_at=bet_with_participants.accepted_at,
            started_at=bet_with_participants.started_at,
            completed_at=bet_with_participants.completed_at,
            resolved_at=bet_with_participants.resolved_at,
            expires_at=bet_with_participants.expires_at,
            creator_id=bet_with_participants.created_by,
            participants=[
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "stake_amount": float(p.stake_amount),
                    "potential_winnings": (
                        float(p.potential_winnings) if p.potential_winnings else None
                    ),
                    "actual_winnings": (
                        float(p.actual_winnings) if p.actual_winnings else None
                    ),
                    "is_active": p.is_active,
                }
                for p in bet_with_participants.participants
            ],
            metadata=bet_with_participants.metadata,
        )

    except RateLimitException as e:
        logger.warning(
            "Rate limit exceeded for bet acceptance", user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to accept bet", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept bet",
        )


@router.post("/resolve", response_model=BetResponse)
@rate_limiter(key="resolve_bet", rate="5/5minute")
async def resolve_bet(
    resolve_data: BetResolveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a bet with comprehensive validation"""
    try:
        betting_service = BettingService(db)

        bet = await betting_service.resolve_bet(
            bet_id=resolve_data.bet_id,
            outcome=resolve_data.outcome,
            resolved_by=current_user.id,
            resolution_data=resolve_data.resolution_data,
            resolution_method=resolve_data.resolution_method,
        )

        # Get bet with participants for response
        bet_with_participants = await betting_service.get_bet(bet.id)

        return BetResponse(
            id=bet_with_participants.id,
            uuid=bet_with_participants.uuid,
            title=bet_with_participants.title,
            description=bet_with_participants.description,
            bet_type=bet_with_participants.bet_type.value,
            status=bet_with_participants.status.value,
            outcome=bet_with_participants.outcome.value,
            amount=float(bet_with_participants.amount),
            commission_amount=float(bet_with_participants.commission_amount),
            total_pot=float(bet_with_participants.total_pot),
            winner_payout=float(bet_with_participants.winner_payout),
            created_at=bet_with_participants.created_at,
            accepted_at=bet_with_participants.accepted_at,
            started_at=bet_with_participants.started_at,
            completed_at=bet_with_participants.completed_at,
            resolved_at=bet_with_participants.resolved_at,
            expires_at=bet_with_participants.expires_at,
            creator_id=bet_with_participants.created_by,
            participants=[
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "stake_amount": float(p.stake_amount),
                    "potential_winnings": (
                        float(p.potential_winnings) if p.potential_winnings else None
                    ),
                    "actual_winnings": (
                        float(p.actual_winnings) if p.actual_winnings else None
                    ),
                    "is_active": p.is_active,
                }
                for p in bet_with_participants.participants
            ],
            metadata=bet_with_participants.metadata,
        )

    except RateLimitException as e:
        logger.warning(
            "Rate limit exceeded for bet resolution", user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to resolve bet", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve bet",
        )


@router.post("/cancel", response_model=BetResponse)
@rate_limiter(key="cancel_bet", rate="10/5minute")
async def cancel_bet(
    cancel_data: BetCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a bet with comprehensive validation"""
    try:
        betting_service = BettingService(db)

        bet = await betting_service.cancel_bet(
            bet_id=cancel_data.bet_id,
            user_id=current_user.id,
            reason=cancel_data.reason,
        )

        # Get bet with participants for response
        bet_with_participants = await betting_service.get_bet(bet.id)

        return BetResponse(
            id=bet_with_participants.id,
            uuid=bet_with_participants.uuid,
            title=bet_with_participants.title,
            description=bet_with_participants.description,
            bet_type=bet_with_participants.bet_type.value,
            status=bet_with_participants.status.value,
            outcome=bet_with_participants.outcome.value,
            amount=float(bet_with_participants.amount),
            commission_amount=float(bet_with_participants.commission_amount),
            total_pot=float(bet_with_participants.total_pot),
            winner_payout=float(bet_with_participants.winner_payout),
            created_at=bet_with_participants.created_at,
            accepted_at=bet_with_participants.accepted_at,
            started_at=bet_with_participants.started_at,
            completed_at=bet_with_participants.completed_at,
            resolved_at=bet_with_participants.resolved_at,
            expires_at=bet_with_participants.expires_at,
            creator_id=bet_with_participants.created_by,
            participants=[
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "stake_amount": float(p.stake_amount),
                    "potential_winnings": (
                        float(p.potential_winnings) if p.potential_winnings else None
                    ),
                    "actual_winnings": (
                        float(p.actual_winnings) if p.actual_winnings else None
                    ),
                    "is_active": p.is_active,
                }
                for p in bet_with_participants.participants
            ],
            metadata=bet_with_participants.metadata,
        )

    except RateLimitException as e:
        logger.warning(
            "Rate limit exceeded for bet cancellation", user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to cancel bet", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel bet",
        )


@router.get("/{bet_id}", response_model=BetResponse)
async def get_bet(
    bet_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific bet by ID"""
    try:
        betting_service = BettingService(db)
        bet = await betting_service.get_bet(bet_id)

        if not bet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Bet not found"
            )

        return BetResponse(
            id=bet.id,
            uuid=bet.uuid,
            title=bet.title,
            description=bet.description,
            bet_type=bet.bet_type.value,
            status=bet.status.value,
            outcome=bet.outcome.value,
            amount=float(bet.amount),
            commission_amount=float(bet.commission_amount),
            total_pot=float(bet.total_pot),
            winner_payout=float(bet.winner_payout),
            created_at=bet.created_at,
            accepted_at=bet.accepted_at,
            started_at=bet.started_at,
            completed_at=bet.completed_at,
            resolved_at=bet.resolved_at,
            expires_at=bet.expires_at,
            creator_id=bet.created_by,
            participants=[
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "stake_amount": float(p.stake_amount),
                    "potential_winnings": (
                        float(p.potential_winnings) if p.potential_winnings else None
                    ),
                    "actual_winnings": (
                        float(p.actual_winnings) if p.actual_winnings else None
                    ),
                    "is_active": p.is_active,
                }
                for p in bet.participants
            ],
            metadata=bet.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get bet", bet_id=bet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bet",
        )


@router.get("/", response_model=BetListResponse)
async def get_user_bets(
    status: Optional[BetStatus] = Query(None, description="Filter by bet status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's bets with optional status filter"""
    try:
        betting_service = BettingService(db)

        offset = (page - 1) * size
        bets = await betting_service.get_user_bets(
            user_id=current_user.id, status=status, limit=size, offset=offset
        )

        # Get total count for pagination
        total_query = select(func.count(Bet.id)).where(
            or_(
                Bet.created_by == current_user.id,
                Bet.participants.any(BetParticipant.user_id == current_user.id),
            )
        )
        if status:
            total_query = total_query.where(Bet.status == status)

        total_result = await db.execute(total_query)
        total = total_result.scalar()

        return BetListResponse(
            items=[
                BetResponse(
                    id=bet.id,
                    uuid=bet.uuid,
                    title=bet.title,
                    description=bet.description,
                    bet_type=bet.bet_type.value,
                    status=bet.status.value,
                    outcome=bet.outcome.value,
                    amount=float(bet.amount),
                    commission_amount=float(bet.commission_amount),
                    total_pot=float(bet.total_pot),
                    winner_payout=float(bet.winner_payout),
                    created_at=bet.created_at,
                    accepted_at=bet.accepted_at,
                    started_at=bet.started_at,
                    completed_at=bet.completed_at,
                    resolved_at=bet.resolved_at,
                    expires_at=bet.expires_at,
                    creator_id=bet.created_by,
                    participants=[
                        {
                            "user_id": p.user_id,
                            "role": p.role.value,
                            "stake_amount": float(p.stake_amount),
                            "potential_winnings": (
                                float(p.potential_winnings)
                                if p.potential_winnings
                                else None
                            ),
                            "actual_winnings": (
                                float(p.actual_winnings) if p.actual_winnings else None
                            ),
                            "is_active": p.is_active,
                        }
                        for p in bet.participants
                    ],
                    metadata=bet.metadata,
                )
                for bet in bets
            ],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )

    except Exception as e:
        logger.error("Failed to get user bets", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user bets",
        )


@router.get("/public/active", response_model=BetListResponse)
async def get_active_bets(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
):
    """Get active bets for public viewing"""
    try:
        betting_service = BettingService(db)

        offset = (page - 1) * size
        bets = await betting_service.get_active_bets(limit=size, offset=offset)

        # Get total count for pagination
        total_result = await db.execute(
            select(func.count(Bet.id)).where(
                Bet.status.in_(
                    [BetStatus.PENDING, BetStatus.ACCEPTED, BetStatus.ACTIVE]
                )
            )
        )
        total = total_result.scalar()

        return BetListResponse(
            items=[
                BetResponse(
                    id=bet.id,
                    uuid=bet.uuid,
                    title=bet.title,
                    description=bet.description,
                    bet_type=bet.bet_type.value,
                    status=bet.status.value,
                    outcome=bet.outcome.value,
                    amount=float(bet.amount),
                    commission_amount=float(bet.commission_amount),
                    total_pot=float(bet.total_pot),
                    winner_payout=float(bet.winner_payout),
                    created_at=bet.created_at,
                    accepted_at=bet.accepted_at,
                    started_at=bet.started_at,
                    completed_at=bet.completed_at,
                    resolved_at=bet.resolved_at,
                    expires_at=bet.expires_at,
                    creator_id=bet.created_by,
                    participants=[
                        {
                            "user_id": p.user_id,
                            "role": p.role.value,
                            "stake_amount": float(p.stake_amount),
                            "potential_winnings": (
                                float(p.potential_winnings)
                                if p.potential_winnings
                                else None
                            ),
                            "actual_winnings": (
                                float(p.actual_winnings) if p.actual_winnings else None
                            ),
                            "is_active": p.is_active,
                        }
                        for p in bet.participants
                    ],
                    metadata=bet.metadata,
                )
                for bet in bets
            ],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )

    except Exception as e:
        logger.error("Failed to get active bets", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active bets",
        )


@router.get("/statistics", response_model=BetStatisticsResponse)
async def get_bet_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's betting statistics"""
    try:
        betting_service = BettingService(db)
        stats = await betting_service.get_bet_statistics(current_user.id)

        return BetStatisticsResponse(**stats)

    except Exception as e:
        logger.error(
            "Failed to get bet statistics", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bet statistics",
        )
