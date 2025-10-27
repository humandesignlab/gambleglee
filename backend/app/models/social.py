"""
Social models for GambleGlee
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
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


class FriendshipStatus(PyEnum):
    """Friendship status enumeration"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    DECLINED = "declined"


class NotificationType(PyEnum):
    """Notification type enumeration"""

    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    BET_INVITATION = "bet_invitation"
    BET_ACCEPTED = "bet_accepted"
    BET_RESOLVED = "bet_resolved"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    TRICK_SHOT_LIKED = "trick_shot_liked"
    TRICK_SHOT_COMMENTED = "trick_shot_commented"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SECURITY_ALERT = "security_alert"


class ActivityType(PyEnum):
    """Activity type enumeration"""

    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    BET_CREATED = "bet_created"
    BET_ACCEPTED = "bet_accepted"
    BET_RESOLVED = "bet_resolved"
    BET_WON = "bet_won"
    BET_LOST = "bet_lost"
    TRICK_SHOT_CREATED = "trick_shot_created"
    TRICK_SHOT_COMPLETED = "trick_shot_completed"
    FRIEND_ADDED = "friend_added"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    PROFILE_UPDATED = "profile_updated"


class PrivacyLevel(PyEnum):
    """Privacy level enumeration"""

    PUBLIC = "public"
    FRIENDS_ONLY = "friends_only"
    PRIVATE = "private"


class UserProfile(Base):
    """Enhanced user profile model"""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Profile information
    bio = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)

    # Social preferences
    privacy_level: Column[PrivacyLevel] = Column(
        Enum(PrivacyLevel), default=PrivacyLevel.PUBLIC, nullable=False
    )
    show_online_status = Column(Boolean, default=True, nullable=False)
    show_activity = Column(Boolean, default=True, nullable=False)
    allow_friend_requests = Column(Boolean, default=True, nullable=False)
    allow_messages = Column(Boolean, default=True, nullable=False)

    # Statistics
    total_bets = Column(Integer, default=0, nullable=False)
    won_bets = Column(Integer, default=0, nullable=False)
    lost_bets = Column(Integer, default=0, nullable=False)
    total_winnings = Column(Float, default=0.0, nullable=False)
    total_losses = Column(Float, default=0.0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)

    # Trick shot statistics
    trick_shots_created = Column(Integer, default=0, nullable=False)
    trick_shots_completed = Column(Integer, default=0, nullable=False)
    trick_shots_liked = Column(Integer, default=0, nullable=False)
    trick_shots_commented = Column(Integer, default=0, nullable=False)

    # Social statistics
    friends_count = Column(Integer, default=0, nullable=False)
    followers_count = Column(Integer, default=0, nullable=False)
    following_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_active = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")
    activities = relationship("UserActivity", back_populates="user_profile")
    achievements = relationship("UserAchievement", back_populates="user_profile")


class Friendship(Base):
    """Friendship model"""

    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Friendship details
    status: Column[FriendshipStatus] = Column(
        Enum(FriendshipStatus), default=FriendshipStatus.PENDING, nullable=False
    )
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Friendship metadata
    is_favorite = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend = relationship("User", foreign_keys=[friend_id], back_populates="friend_of")
    initiator = relationship("User", foreign_keys=[initiated_by])

    # Constraints
    __table_args__ = (
        # Ensure unique friendship pairs
        # UniqueConstraint('user_id', 'friend_id', name='_user_friend_uc'),
        # Ensure user can't be friends with themselves
        # CheckConstraint('user_id != friend_id', name='_no_self_friendship'),
    )


class UserActivity(Base):
    """User activity model for activity feeds"""

    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)

    # Activity details
    activity_type: Column[ActivityType] = Column(Enum(ActivityType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Activity metadata
    metadata = Column(JSON, nullable=True)  # Store additional activity data
    is_public = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    # Engagement metrics
    likes_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    shares_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User")
    user_profile = relationship("UserProfile", back_populates="activities")
    likes = relationship(
        "ActivityLike", back_populates="activity", cascade="all, delete-orphan"
    )
    comments = relationship(
        "ActivityComment", back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityLike(Base):
    """Activity like model"""

    __tablename__ = "activity_likes"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("user_activities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Like metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    activity = relationship("UserActivity", back_populates="likes")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        # Ensure unique likes per user per activity
        # UniqueConstraint('activity_id', 'user_id', name='_activity_user_like_uc'),
    )


class ActivityComment(Base):
    """Activity comment model"""

    __tablename__ = "activity_comments"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("user_activities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Comment details
    content = Column(Text, nullable=False)
    parent_comment_id = Column(
        Integer, ForeignKey("activity_comments.id"), nullable=True
    )

    # Comment metadata
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement metrics
    likes_count = Column(Integer, default=0, nullable=False)
    replies_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    activity = relationship("UserActivity", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("ActivityComment", remote_side=[id])
    replies = relationship("ActivityComment", back_populates="parent_comment")


class Notification(Base):
    """Notification model"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification details
    notification_type: Column[NotificationType] = Column(
        Enum(NotificationType), nullable=False
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Notification metadata
    is_read = Column(Boolean, default=False, nullable=False)
    is_important = Column(Boolean, default=False, nullable=False)
    action_url = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")


class UserAchievement(Base):
    """User achievement model"""

    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)

    # Achievement details
    achievement_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon_url = Column(String(500), nullable=True)

    # Achievement metadata
    points = Column(Integer, default=0, nullable=False)
    rarity = Column(
        String(20), default="common", nullable=False
    )  # common, rare, epic, legendary
    category = Column(
        String(50), nullable=False
    )  # betting, social, trick_shot, general

    # Timestamps
    unlocked_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User")
    user_profile = relationship("UserProfile", back_populates="achievements")


class Leaderboard(Base):
    """Leaderboard model"""

    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True, index=True)

    # Leaderboard details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        String(50), nullable=False
    )  # betting, trick_shot, social, general

    # Leaderboard configuration
    metric = Column(
        String(50), nullable=False
    )  # win_rate, total_winnings, friends_count, etc.
    time_period = Column(
        String(20), default="all_time", nullable=False
    )  # daily, weekly, monthly, all_time
    max_entries = Column(Integer, default=100, nullable=False)

    # Leaderboard status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_updated = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    entries = relationship(
        "LeaderboardEntry", back_populates="leaderboard", cascade="all, delete-orphan"
    )


class LeaderboardEntry(Base):
    """Leaderboard entry model"""

    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, index=True)
    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Entry details
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    leaderboard = relationship("Leaderboard", back_populates="entries")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        # Ensure unique user per leaderboard
        # UniqueConstraint('leaderboard_id', 'user_id', name='_leaderboard_user_uc'),
    )


class UserSearch(Base):
    """User search model for search analytics"""

    __tablename__ = "user_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Nullable for anonymous searches

    # Search details
    query = Column(String(255), nullable=False)
    search_type = Column(
        String(50), default="user", nullable=False
    )  # user, bet, trick_shot
    filters = Column(JSON, nullable=True)

    # Search results
    results_count = Column(Integer, default=0, nullable=False)
    clicked_result_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User")
