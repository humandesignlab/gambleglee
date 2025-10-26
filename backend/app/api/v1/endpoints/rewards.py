"""
Rewards API endpoints for GambleGlee
"""

from datetime import datetime
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import InsufficientFundsError, ValidationError
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.rewards_service import RewardsService

logger = structlog.get_logger(__name__)

router = APIRouter()

# === PYDANTIC SCHEMAS ===


class TrickShooterRewardRequest(BaseModel):
    """Request to create trick shooter reward"""

    event_id: int = Field(..., description="ID of the trick shot event")
    viewer_count: int = Field(0, description="Number of viewers")
    bet_count: int = Field(0, description="Number of bets placed")
    completion_status: bool = Field(
        False, description="Whether trick shot was completed"
    )
    community_rating: float = Field(
        0.0, ge=0.0, le=5.0, description="Community rating (0-5)"
    )


class FriendBetRewardRequest(BaseModel):
    """Request to create friend bet reward"""

    bet_id: int = Field(..., description="ID of the friend bet")
    bet_amount: float = Field(..., gt=0, description="Amount of the bet")
    acceptance_status: bool = Field(False, description="Whether bet was accepted")
    completion_status: bool = Field(False, description="Whether bet was completed")
    social_interactions: int = Field(0, description="Number of social interactions")


class PointsRedemptionRequest(BaseModel):
    """Request to redeem points"""

    redemption_type: str = Field(
        ...,
        description="Type of redemption (cash, betting_credit, merchandise, premium)",
    )
    points_used: int = Field(..., gt=0, description="Points to redeem")
    value_received: float = Field(
        ..., gt=0, description="Value received for redemption"
    )


class CreatorProgramRequest(BaseModel):
    """Request to enroll in creator program"""

    program_type: str = Field(
        ..., description="Type of creator program (trick_shooter, influencer)"
    )
    requirements_met: Dict[str, Any] = Field(
        ..., description="Requirements met for enrollment"
    )


class RewardResponse(BaseModel):
    """Response for reward creation"""

    reward_id: int
    user_id: int
    reward_type: str
    points_earned: int
    cash_earned: float
    description: str
    status: str
    created_at: datetime


class UserRewardsSummary(BaseModel):
    """User rewards summary"""

    total_points: int
    current_tier: str
    tier_progress: float
    bonus_rate: float
    recent_rewards: List[Dict[str, Any]]
    completed_achievements: int


class TrickShooterRewardResponse(BaseModel):
    """Trick shooter reward response"""

    id: int
    user_id: int
    event_id: int
    event_creation_bonus: float
    viewer_bonus: float
    engagement_bonus: float
    completion_bonus: float
    rating_bonus: float
    recurring_bonus: float
    total_reward: float
    viewer_count: int
    bet_count: int
    completion_status: bool
    community_rating: float
    created_at: datetime


class FriendBetRewardResponse(BaseModel):
    """Friend bet reward response"""

    id: int
    user_id: int
    bet_id: int
    creation_bonus: float
    acceptance_bonus: float
    completion_bonus: float
    social_bonus: float
    community_bonus: float
    total_reward: float
    bet_amount: float
    acceptance_status: bool
    completion_status: bool
    social_interactions: int
    created_at: datetime


# === API ENDPOINTS ===


@router.get("/summary", response_model=UserRewardsSummary)
async def get_user_rewards_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's rewards summary"""
    try:
        rewards_service = RewardsService(db)
        summary = await rewards_service.get_user_rewards_summary(current_user.id)
        return UserRewardsSummary(**summary)
    except Exception as e:
        logger.error(
            "Failed to get rewards summary", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rewards summary",
        )


@router.post("/trick-shooter", response_model=TrickShooterRewardResponse)
async def create_trick_shooter_reward(
    reward_data: TrickShooterRewardRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create reward for trick shooter event"""
    try:
        rewards_service = RewardsService(db)
        reward = await rewards_service.create_trick_shooter_reward(
            user_id=current_user.id,
            event_id=reward_data.event_id,
            viewer_count=reward_data.viewer_count,
            bet_count=reward_data.bet_count,
            completion_status=reward_data.completion_status,
            community_rating=reward_data.community_rating,
        )

        return TrickShooterRewardResponse(
            id=reward.id,
            user_id=reward.user_id,
            event_id=reward.event_id,
            event_creation_bonus=reward.event_creation_bonus,
            viewer_bonus=reward.viewer_bonus,
            engagement_bonus=reward.engagement_bonus,
            completion_bonus=reward.completion_bonus,
            rating_bonus=reward.rating_bonus,
            recurring_bonus=reward.recurring_bonus,
            total_reward=reward.total_reward,
            viewer_count=reward.viewer_count,
            bet_count=reward.bet_count,
            completion_status=reward.completion_status,
            community_rating=reward.community_rating,
            created_at=reward.created_at,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to create trick shooter reward",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trick shooter reward",
        )


@router.post("/friend-bet", response_model=FriendBetRewardResponse)
async def create_friend_bet_reward(
    reward_data: FriendBetRewardRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create reward for friend bet"""
    try:
        rewards_service = RewardsService(db)
        reward = await rewards_service.create_friend_bet_reward(
            user_id=current_user.id,
            bet_id=reward_data.bet_id,
            bet_amount=reward_data.bet_amount,
            acceptance_status=reward_data.acceptance_status,
            completion_status=reward_data.completion_status,
            social_interactions=reward_data.social_interactions,
        )

        return FriendBetRewardResponse(
            id=reward.id,
            user_id=reward.user_id,
            bet_id=reward.bet_id,
            creation_bonus=reward.creation_bonus,
            acceptance_bonus=reward.acceptance_bonus,
            completion_bonus=reward.completion_bonus,
            social_bonus=reward.social_bonus,
            community_bonus=reward.community_bonus,
            total_reward=reward.total_reward,
            bet_amount=reward.bet_amount,
            acceptance_status=reward.acceptance_status,
            completion_status=reward.completion_status,
            social_interactions=reward.social_interactions,
            created_at=reward.created_at,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to create friend bet reward", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create friend bet reward",
        )


@router.post("/redeem-points")
async def redeem_points(
    redemption_data: PointsRedemptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem points for rewards"""
    try:
        rewards_service = RewardsService(db)
        redemption = await rewards_service.redeem_points(
            user_id=current_user.id,
            redemption_type=redemption_data.redemption_type,
            points_used=redemption_data.points_used,
            value_received=redemption_data.value_received,
        )

        return {
            "redemption_id": redemption.id,
            "user_id": redemption.user_id,
            "redemption_type": redemption.redemption_type,
            "points_used": redemption.points_used,
            "value_received": redemption.value_received,
            "status": redemption.status,
            "created_at": redemption.created_at,
        }
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to redeem points", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to redeem points",
        )


@router.post("/creator-program")
async def enroll_creator_program(
    program_data: CreatorProgramRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Enroll in creator program"""
    try:
        rewards_service = RewardsService(db)
        program = await rewards_service.enroll_creator_program(
            user_id=current_user.id,
            program_type=program_data.program_type,
            requirements_met=program_data.requirements_met,
        )

        return {
            "program_id": program.id,
            "user_id": program.user_id,
            "program_type": program.program_type,
            "status": program.status,
            "enrollment_date": program.enrollment_date,
            "benefits": program.benefits,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to enroll in creator program", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enroll in creator program",
        )


@router.get("/points")
async def get_user_points(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's total points"""
    try:
        rewards_service = RewardsService(db)
        total_points = await rewards_service.get_user_points(current_user.id)

        return {"user_id": current_user.id, "total_points": total_points}
    except Exception as e:
        logger.error("Failed to get user points", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user points",
        )


@router.get("/tier")
async def get_user_tier(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's current tier"""
    try:
        rewards_service = RewardsService(db)
        tier_info = await rewards_service.get_user_tier(current_user.id)

        return {
            "user_id": current_user.id,
            "current_tier": tier_info.current_tier.value,
            "total_points": tier_info.total_points,
            "tier_points": tier_info.tier_points,
            "tier_progress": tier_info.tier_progress,
            "bonus_rate": tier_info.bonus_rate,
        }
    except Exception as e:
        logger.error("Failed to get user tier", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user tier",
        )


@router.post("/check-achievements")
async def check_achievements(
    achievement_type: str,
    progress: int = 1,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check and update user achievements"""
    try:
        rewards_service = RewardsService(db)
        await rewards_service.check_achievements(
            user_id=current_user.id,
            achievement_type=achievement_type,
            progress=progress,
        )

        return {
            "user_id": current_user.id,
            "achievement_type": achievement_type,
            "progress": progress,
            "status": "checked",
        }
    except Exception as e:
        logger.error(
            "Failed to check achievements", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check achievements",
        )
