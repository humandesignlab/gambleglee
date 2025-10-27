"""
Rewards system models for GambleGlee
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RewardType(PyEnum):
    """Types of rewards that can be earned"""

    TRICK_SHOT_EVENT = "trick_shot_event"
    TRICK_SHOT_VIEWER = "trick_shot_viewer"
    TRICK_SHOT_ENGAGEMENT = "trick_shot_engagement"
    TRICK_SHOT_COMPLETION = "trick_shot_completion"
    TRICK_SHOT_RATING = "trick_shot_rating"
    FRIEND_BET_CREATION = "friend_bet_creation"
    FRIEND_BET_ACCEPTANCE = "friend_bet_acceptance"
    FRIEND_BET_COMPLETION = "friend_bet_completion"
    SOCIAL_ENGAGEMENT = "social_engagement"
    COMMUNITY_BUILDING = "community_building"
    REFERRAL = "referral"
    ACHIEVEMENT = "achievement"
    TIER_BONUS = "tier_bonus"


class RewardStatus(PyEnum):
    """Status of rewards"""

    PENDING = "pending"
    APPROVED = "approved"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class UserTier(PyEnum):
    """User tier levels"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class Reward(Base):
    """Reward earned by a user"""

    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_type: Column[RewardType] = Column(Enum(RewardType), nullable=False)
    points_earned = Column(Integer, nullable=False, default=0)
    cash_earned = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=True)
    status: Column[RewardStatus] = Column(Enum(RewardStatus), default=RewardStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign key relationships
    user = relationship("User", back_populates="rewards")

    # Additional metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data
    source_id = Column(Integer, nullable=True)  # ID of the source (event, bet, etc.)
    source_type = Column(String(50), nullable=True)  # Type of source


class UserTierInfo(Base):
    """User tier information and progress"""

    __tablename__ = "user_tier_info"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_tier: Column[UserTier] = Column(Enum(UserTier), default=UserTier.BRONZE)
    total_points = Column(Integer, default=0)
    tier_points = Column(Integer, default=0)  # Points in current tier
    tier_progress = Column(Float, default=0.0)  # Progress to next tier (0-100)
    bonus_rate = Column(Float, default=0.0)  # Bonus rate for current tier
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Foreign key relationships
    user = relationship("User", back_populates="tier_info")


class TrickShooterReward(Base):
    """Rewards specifically for trick shooters"""

    __tablename__ = "trick_shooter_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, nullable=False)  # ID of the trick shot event
    event_creation_bonus = Column(Float, default=0.0)
    viewer_bonus = Column(Float, default=0.0)
    engagement_bonus = Column(Float, default=0.0)
    completion_bonus = Column(Float, default=0.0)
    rating_bonus = Column(Float, default=0.0)
    recurring_bonus = Column(Float, default=0.0)
    total_reward = Column(Float, default=0.0)
    viewer_count = Column(Integer, default=0)
    bet_count = Column(Integer, default=0)
    completion_status = Column(Boolean, default=False)
    community_rating = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key relationships
    user = relationship("User", back_populates="trick_shooter_rewards")


class FriendBetReward(Base):
    """Rewards specifically for friend bet initiators"""

    __tablename__ = "friend_bet_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bet_id = Column(Integer, nullable=False)  # ID of the friend bet
    creation_bonus = Column(Float, default=0.0)
    acceptance_bonus = Column(Float, default=0.0)
    completion_bonus = Column(Float, default=0.0)
    social_bonus = Column(Float, default=0.0)
    community_bonus = Column(Float, default=0.0)
    total_reward = Column(Float, default=0.0)
    bet_amount = Column(Float, default=0.0)
    acceptance_status = Column(Boolean, default=False)
    completion_status = Column(Boolean, default=False)
    social_interactions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key relationships
    user = relationship("User", back_populates="friend_bet_rewards")


class PointsTransaction(Base):
    """Points transaction history"""

    __tablename__ = "points_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(
        String(50), nullable=False
    )  # 'earned', 'redeemed', 'expired'
    points_amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    source_id = Column(Integer, nullable=True)  # ID of the source
    source_type = Column(String(50), nullable=True)  # Type of source
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key relationships
    user = relationship("User", back_populates="points_transactions")


class RewardRedemption(Base):
    """Reward redemption history"""

    __tablename__ = "reward_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    redemption_type = Column(
        String(50), nullable=False
    )  # 'cash', 'betting_credit', 'merchandise', 'premium'
    points_used = Column(Integer, nullable=False)
    value_received = Column(Float, nullable=False)
    status = Column(
        String(50), default="pending"
    )  # 'pending', 'approved', 'completed', 'cancelled'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign key relationships
    user = relationship("User", back_populates="reward_redemptions")
    reward = relationship("Reward")


class Achievement(Base):
    """Achievement definitions and user progress"""

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    points_reward = Column(Integer, default=0)
    cash_reward = Column(Float, default=0.0)
    requirements = Column(Text, nullable=True)  # JSON string for requirements
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """User achievement progress and completion"""

    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key relationships
    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class CreatorProgram(Base):
    """Creator program enrollment and benefits"""

    __tablename__ = "creator_program"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    program_type = Column(String(50), nullable=False)  # 'trick_shooter', 'influencer'
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="active")  # 'active', 'suspended', 'terminated'
    benefits = Column(Text, nullable=True)  # JSON string for benefits
    requirements_met = Column(Text, nullable=True)  # JSON string for requirements
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Foreign key relationships
    user = relationship("User", back_populates="creator_program")


class SeasonalReward(Base):
    """Seasonal and special rewards"""

    __tablename__ = "seasonal_rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    reward_type = Column(
        String(50), nullable=False
    )  # 'holiday', 'special_event', 'anniversary'
    points_multiplier = Column(Float, default=1.0)
    cash_multiplier = Column(Float, default=1.0)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_seasonal_rewards = relationship(
        "UserSeasonalReward", back_populates="seasonal_reward"
    )


class UserSeasonalReward(Base):
    """User participation in seasonal rewards"""

    __tablename__ = "user_seasonal_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seasonal_reward_id = Column(
        Integer, ForeignKey("seasonal_rewards.id"), nullable=False
    )
    points_earned = Column(Integer, default=0)
    cash_earned = Column(Float, default=0.0)
    participation_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign key relationships
    user = relationship("User", back_populates="user_seasonal_rewards")
    seasonal_reward = relationship(
        "SeasonalReward", back_populates="user_seasonal_rewards"
    )
