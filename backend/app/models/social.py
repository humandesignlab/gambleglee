"""
Social features models
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class FriendshipStatus(str, enum.Enum):
    """Friendship status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class NotificationType(str, enum.Enum):
    """Notification types"""
    BET_INVITATION = "bet_invitation"
    BET_RESOLVED = "bet_resolved"
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    TRICK_SHOT_EVENT = "trick_shot_event"
    BALANCE_UPDATE = "balance_update"


class Friendship(Base):
    """Friendship model"""
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="friendships", foreign_keys=[user_id])
    friend = relationship("User", back_populates="friend_of", foreign_keys=[friend_id])


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification details
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    # Related entities
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=True)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trick_shot_event_id = Column(Integer, ForeignKey("trick_shot_events.id"), nullable=True)

    # Metadata
    metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    bet = relationship("Bet")
    friend = relationship("User", foreign_keys=[friend_id])
    trick_shot_event = relationship("TrickShotEvent")
