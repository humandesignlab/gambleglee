"""
Rewards service for GambleGlee
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import json

from app.models.rewards import (
    Reward, RewardType, RewardStatus, UserTier, UserTierInfo,
    TrickShooterReward, FriendBetReward, PointsTransaction,
    RewardRedemption, Achievement, UserAchievement,
    CreatorProgram, SeasonalReward, UserSeasonalReward
)
from app.models.user import User
from app.core.exceptions import ValidationError, InsufficientFundsError
import structlog

logger = structlog.get_logger(__name__)

class RewardsService:
    """Service for managing rewards and points system"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === TIER MANAGEMENT ===

    async def get_user_tier(self, user_id: int) -> UserTierInfo:
        """Get user's current tier information"""
        result = await self.db.execute(
            select(UserTierInfo).where(UserTierInfo.user_id == user_id)
        )
        tier_info = result.scalar_one_or_none()

        if not tier_info:
            # Create initial tier info
            tier_info = UserTierInfo(
                user_id=user_id,
                current_tier=UserTier.BRONZE,
                total_points=0,
                tier_points=0,
                tier_progress=0.0,
                bonus_rate=0.0
            )
            self.db.add(tier_info)
            await self.db.commit()

        return tier_info

    async def update_user_tier(self, user_id: int, points_earned: int) -> UserTierInfo:
        """Update user tier based on total points"""
        tier_info = await self.get_user_tier(user_id)

        # Update total points
        tier_info.total_points += points_earned
        tier_info.tier_points += points_earned

        # Calculate new tier
        new_tier = self._calculate_tier(tier_info.total_points)
        tier_info.current_tier = new_tier

        # Calculate tier progress
        tier_info.tier_progress = self._calculate_tier_progress(tier_info.total_points, new_tier)

        # Calculate bonus rate
        tier_info.bonus_rate = self._calculate_bonus_rate(new_tier)

        await self.db.commit()
        return tier_info

    def _calculate_tier(self, total_points: int) -> UserTier:
        """Calculate user tier based on total points"""
        if total_points >= 25000:
            return UserTier.DIAMOND
        elif total_points >= 10000:
            return UserTier.PLATINUM
        elif total_points >= 5000:
            return UserTier.GOLD
        elif total_points >= 1000:
            return UserTier.SILVER
        else:
            return UserTier.BRONZE

    def _calculate_tier_progress(self, total_points: int, current_tier: UserTier) -> float:
        """Calculate progress to next tier (0-100)"""
        tier_thresholds = {
            UserTier.BRONZE: 0,
            UserTier.SILVER: 1000,
            UserTier.GOLD: 5000,
            UserTier.PLATINUM: 10000,
            UserTier.DIAMOND: 25000
        }

        current_threshold = tier_thresholds[current_tier]
        next_threshold = tier_thresholds.get(self._get_next_tier(current_tier), current_threshold)

        if next_threshold == current_threshold:
            return 100.0  # Already at highest tier

        progress = ((total_points - current_threshold) / (next_threshold - current_threshold)) * 100
        return min(100.0, max(0.0, progress))

    def _get_next_tier(self, current_tier: UserTier) -> Optional[UserTier]:
        """Get next tier level"""
        tier_order = [UserTier.BRONZE, UserTier.SILVER, UserTier.GOLD, UserTier.PLATINUM, UserTier.DIAMOND]
        current_index = tier_order.index(current_tier)
        if current_index < len(tier_order) - 1:
            return tier_order[current_index + 1]
        return None

    def _calculate_bonus_rate(self, tier: UserTier) -> float:
        """Calculate bonus rate for tier"""
        bonus_rates = {
            UserTier.BRONZE: 0.0,
            UserTier.SILVER: 0.10,
            UserTier.GOLD: 0.20,
            UserTier.PLATINUM: 0.30,
            UserTier.DIAMOND: 0.50
        }
        return bonus_rates.get(tier, 0.0)

    # === TRICK SHOOTER REWARDS ===

    async def create_trick_shooter_reward(
        self,
        user_id: int,
        event_id: int,
        viewer_count: int = 0,
        bet_count: int = 0,
        completion_status: bool = False,
        community_rating: float = 0.0
    ) -> TrickShooterReward:
        """Create reward for trick shooter event"""
        tier_info = await self.get_user_tier(user_id)

        # Calculate rewards based on tier
        base_rewards = self._calculate_trick_shooter_rewards(
            tier_info.current_tier, viewer_count, bet_count, completion_status, community_rating
        )

        # Apply tier bonus
        bonus_multiplier = 1.0 + tier_info.bonus_rate
        total_reward = sum(base_rewards.values()) * bonus_multiplier

        trick_shooter_reward = TrickShooterReward(
            user_id=user_id,
            event_id=event_id,
            event_creation_bonus=base_rewards["event_creation"] * bonus_multiplier,
            viewer_bonus=base_rewards["viewer_bonus"] * bonus_multiplier,
            engagement_bonus=base_rewards["engagement_bonus"] * bonus_multiplier,
            completion_bonus=base_rewards["completion_bonus"] * bonus_multiplier,
            rating_bonus=base_rewards["rating_bonus"] * bonus_multiplier,
            recurring_bonus=base_rewards["recurring_bonus"] * bonus_multiplier,
            total_reward=total_reward,
            viewer_count=viewer_count,
            bet_count=bet_count,
            completion_status=completion_status,
            community_rating=community_rating
        )

        self.db.add(trick_shooter_reward)
        await self.db.commit()

        # Create points transaction
        points_earned = int(total_reward * 100)  # $1 = 100 points
        await self._create_points_transaction(
            user_id, "earned", points_earned,
            f"Trick shooter reward for event {event_id}"
        )

        # Update user tier
        await self.update_user_tier(user_id, points_earned)

        logger.info("Trick shooter reward created",
                   user_id=user_id, event_id=event_id, total_reward=total_reward)

        return trick_shooter_reward

    def _calculate_trick_shooter_rewards(
        self,
        tier: UserTier,
        viewer_count: int,
        bet_count: int,
        completion_status: bool,
        community_rating: float
    ) -> Dict[str, float]:
        """Calculate trick shooter rewards based on tier and performance"""
        base_rewards = {
            "event_creation": 5.0,
            "viewer_bonus": 0.10,
            "engagement_bonus": 0.05,
            "completion_bonus": 10.0,
            "rating_bonus": 5.0,
            "recurring_bonus": 0.0
        }

        # Adjust base rewards based on tier
        tier_multipliers = {
            UserTier.BRONZE: 1.0,
            UserTier.SILVER: 1.2,
            UserTier.GOLD: 1.5,
            UserTier.PLATINUM: 2.0,
            UserTier.DIAMOND: 2.5
        }

        multiplier = tier_multipliers.get(tier, 1.0)

        # Calculate actual rewards
        rewards = {
            "event_creation": base_rewards["event_creation"] * multiplier,
            "viewer_bonus": base_rewards["viewer_bonus"] * viewer_count * multiplier,
            "engagement_bonus": base_rewards["engagement_bonus"] * bet_count * multiplier,
            "completion_bonus": base_rewards["completion_bonus"] * multiplier if completion_status else 0.0,
            "rating_bonus": base_rewards["rating_bonus"] * (community_rating / 5.0) * multiplier,
            "recurring_bonus": base_rewards["recurring_bonus"] * multiplier
        }

        return rewards

    # === FRIEND BET REWARDS ===

    async def create_friend_bet_reward(
        self,
        user_id: int,
        bet_id: int,
        bet_amount: float,
        acceptance_status: bool = False,
        completion_status: bool = False,
        social_interactions: int = 0
    ) -> FriendBetReward:
        """Create reward for friend bet"""
        tier_info = await self.get_user_tier(user_id)

        # Calculate rewards based on tier
        base_rewards = self._calculate_friend_bet_rewards(
            tier_info.current_tier, bet_amount, acceptance_status, completion_status, social_interactions
        )

        # Apply tier bonus
        bonus_multiplier = 1.0 + tier_info.bonus_rate
        total_reward = sum(base_rewards.values()) * bonus_multiplier

        friend_bet_reward = FriendBetReward(
            user_id=user_id,
            bet_id=bet_id,
            creation_bonus=base_rewards["creation_bonus"] * bonus_multiplier,
            acceptance_bonus=base_rewards["acceptance_bonus"] * bonus_multiplier,
            completion_bonus=base_rewards["completion_bonus"] * bonus_multiplier,
            social_bonus=base_rewards["social_bonus"] * bonus_multiplier,
            community_bonus=base_rewards["community_bonus"] * bonus_multiplier,
            total_reward=total_reward,
            bet_amount=bet_amount,
            acceptance_status=acceptance_status,
            completion_status=completion_status,
            social_interactions=social_interactions
        )

        self.db.add(friend_bet_reward)
        await self.db.commit()

        # Create points transaction
        points_earned = int(total_reward * 100)  # $1 = 100 points
        await self._create_points_transaction(
            user_id, "earned", points_earned,
            f"Friend bet reward for bet {bet_id}"
        )

        # Update user tier
        await self.update_user_tier(user_id, points_earned)

        logger.info("Friend bet reward created",
                   user_id=user_id, bet_id=bet_id, total_reward=total_reward)

        return friend_bet_reward

    def _calculate_friend_bet_rewards(
        self,
        tier: UserTier,
        bet_amount: float,
        acceptance_status: bool,
        completion_status: bool,
        social_interactions: int
    ) -> Dict[str, float]:
        """Calculate friend bet rewards based on tier and performance"""
        base_rewards = {
            "creation_bonus": 1.0,
            "acceptance_bonus": 2.0,
            "completion_bonus": 3.0,
            "social_bonus": 0.50,
            "community_bonus": 5.0
        }

        # Adjust base rewards based on tier
        tier_multipliers = {
            UserTier.BRONZE: 1.0,
            UserTier.SILVER: 1.2,
            UserTier.GOLD: 1.5,
            UserTier.PLATINUM: 2.0,
            UserTier.DIAMOND: 2.5
        }

        multiplier = tier_multipliers.get(tier, 1.0)

        # Calculate actual rewards
        rewards = {
            "creation_bonus": base_rewards["creation_bonus"] * multiplier,
            "acceptance_bonus": base_rewards["acceptance_bonus"] * multiplier if acceptance_status else 0.0,
            "completion_bonus": base_rewards["completion_bonus"] * multiplier if completion_status else 0.0,
            "social_bonus": base_rewards["social_bonus"] * social_interactions * multiplier,
            "community_bonus": base_rewards["community_bonus"] * multiplier
        }

        return rewards

    # === POINTS MANAGEMENT ===

    async def _create_points_transaction(
        self,
        user_id: int,
        transaction_type: str,
        points_amount: int,
        description: str,
        source_id: Optional[int] = None,
        source_type: Optional[str] = None
    ) -> PointsTransaction:
        """Create a points transaction"""
        transaction = PointsTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            points_amount=points_amount,
            description=description,
            source_id=source_id,
            source_type=source_type
        )

        self.db.add(transaction)
        await self.db.commit()

        return transaction

    async def get_user_points(self, user_id: int) -> int:
        """Get user's total points"""
        result = await self.db.execute(
            select(func.sum(PointsTransaction.points_amount))
            .where(PointsTransaction.user_id == user_id)
        )
        total_points = result.scalar() or 0
        return total_points

    async def redeem_points(
        self,
        user_id: int,
        redemption_type: str,
        points_used: int,
        value_received: float
    ) -> RewardRedemption:
        """Redeem points for rewards"""
        # Check if user has enough points
        user_points = await self.get_user_points(user_id)
        if user_points < points_used:
            raise InsufficientFundsError("Not enough points for redemption")

        # Create redemption record
        redemption = RewardRedemption(
            user_id=user_id,
            reward_id=0,  # Will be updated when reward is created
            redemption_type=redemption_type,
            points_used=points_used,
            value_received=value_received,
            status="pending"
        )

        self.db.add(redemption)
        await self.db.commit()

        # Create points transaction
        await self._create_points_transaction(
            user_id, "redeemed", -points_used,
            f"Points redemption: {redemption_type}"
        )

        logger.info("Points redeemed",
                   user_id=user_id, points_used=points_used, value_received=value_received)

        return redemption

    # === ACHIEVEMENT SYSTEM ===

    async def check_achievements(self, user_id: int, achievement_type: str, progress: int = 1):
        """Check and update user achievements"""
        # Get all active achievements
        result = await self.db.execute(
            select(Achievement).where(Achievement.is_active == True)
        )
        achievements = result.scalars().all()

        for achievement in achievements:
            # Check if user already has this achievement
            existing = await self.db.execute(
                select(UserAchievement).where(
                    and_(
                        UserAchievement.user_id == user_id,
                        UserAchievement.achievement_id == achievement.id
                    )
                )
            )
            user_achievement = existing.scalar_one_or_none()

            if not user_achievement:
                # Create new user achievement
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    progress=progress
                )
                self.db.add(user_achievement)
            else:
                # Update existing achievement
                user_achievement.progress += progress

            # Check if achievement is completed
            if user_achievement.progress >= self._get_achievement_requirement(achievement):
                if not user_achievement.is_completed:
                    user_achievement.is_completed = True
                    user_achievement.completed_at = datetime.utcnow()

                    # Award achievement rewards
                    if achievement.points_reward > 0:
                        await self._create_points_transaction(
                            user_id, "earned", achievement.points_reward,
                            f"Achievement: {achievement.name}"
                        )

                    logger.info("Achievement completed",
                               user_id=user_id, achievement_id=achievement.id)

        await self.db.commit()

    def _get_achievement_requirement(self, achievement: Achievement) -> int:
        """Get achievement requirement (simplified for now)"""
        # This would parse the requirements JSON and return the required value
        # For now, return a default value
        return 1

    # === CREATOR PROGRAM ===

    async def enroll_creator_program(
        self,
        user_id: int,
        program_type: str,
        requirements_met: Dict
    ) -> CreatorProgram:
        """Enroll user in creator program"""
        # Check if user is already enrolled
        existing = await self.db.execute(
            select(CreatorProgram).where(CreatorProgram.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            raise ValidationError("User already enrolled in creator program")

        creator_program = CreatorProgram(
            user_id=user_id,
            program_type=program_type,
            status="active",
            benefits=json.dumps(self._get_creator_benefits(program_type)),
            requirements_met=json.dumps(requirements_met)
        )

        self.db.add(creator_program)
        await self.db.commit()

        logger.info("Creator program enrollment",
                   user_id=user_id, program_type=program_type)

        return creator_program

    def _get_creator_benefits(self, program_type: str) -> Dict:
        """Get creator program benefits"""
        benefits = {
            "trick_shooter": {
                "enhanced_rewards": "Double points and cash rewards",
                "exclusive_features": "Advanced analytics, custom branding",
                "merchandise": "Free GambleGlee merchandise",
                "events": "Exclusive creator events and meetups",
                "recognition": "Creator badge, featured placement",
                "support": "Dedicated creator support team"
            },
            "influencer": {
                "enhanced_rewards": "Triple points and cash rewards",
                "exclusive_features": "Advanced social features, custom themes",
                "merchandise": "Free GambleGlee merchandise",
                "events": "Exclusive influencer events",
                "recognition": "Influencer badge, featured placement",
                "support": "Dedicated influencer support team"
            }
        }
        return benefits.get(program_type, {})

    # === REWARDS ANALYTICS ===

    async def get_user_rewards_summary(self, user_id: int) -> Dict:
        """Get user's rewards summary"""
        # Get total points
        total_points = await self.get_user_points(user_id)

        # Get tier info
        tier_info = await self.get_user_tier(user_id)

        # Get recent rewards
        result = await self.db.execute(
            select(Reward).where(Reward.user_id == user_id)
            .order_by(Reward.created_at.desc())
            .limit(10)
        )
        recent_rewards = result.scalars().all()

        # Get achievements
        result = await self.db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.is_completed == True
                )
            )
        )
        completed_achievements = result.scalars().all()

        return {
            "total_points": total_points,
            "current_tier": tier_info.current_tier.value,
            "tier_progress": tier_info.tier_progress,
            "bonus_rate": tier_info.bonus_rate,
            "recent_rewards": [
                {
                    "type": reward.reward_type.value,
                    "points": reward.points_earned,
                    "cash": reward.cash_earned,
                    "description": reward.description,
                    "created_at": reward.created_at
                } for reward in recent_rewards
            ],
            "completed_achievements": len(completed_achievements)
        }
