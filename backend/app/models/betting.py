"""
Betting models
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class BetType(str, enum.Enum):
    """Bet types"""
    BINARY = "binary"  # Yes/No
    TIME_BASED = "time_based"  # Time range prediction
    MULTI_OUTCOME = "multi_outcome"  # A, B, or C
    TRICK_SHOT = "trick_shot"  # Live trick shot betting


class BetStatus(str, enum.Enum):
    """Bet status"""
    PENDING = "pending"  # Waiting for participants
    ACTIVE = "active"  # Betting is open
    LOCKED = "locked"  # No more participants, waiting for outcome
    RESOLVED = "resolved"  # Outcome determined, funds distributed
    CANCELLED = "cancelled"  # Bet cancelled, funds returned


class BetOutcome(str, enum.Enum):
    """Bet outcomes"""
    PENDING = "pending"
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"  # Tie/refund


class Bet(Base):
    """Bet model"""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Bet details
    type = Column(Enum(BetType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)  # Amount per participant

    # Bet configuration
    max_participants = Column(Integer, nullable=True)  # None = unlimited
    min_participants = Column(Integer, default=2, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Status and outcome
    status = Column(Enum(BetStatus), default=BetStatus.PENDING)
    outcome = Column(Enum(BetOutcome), default=BetOutcome.PENDING)
    resolution_notes = Column(Text, nullable=True)

    # Trick shot specific
    trick_shot_event_id = Column(Integer, ForeignKey("trick_shot_events.id"), nullable=True)
    time_limit_seconds = Column(Integer, nullable=True)  # For time-based bets

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    locked_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator = relationship("User", back_populates="created_bets", foreign_keys=[creator_id])
    participants = relationship("BetParticipant", back_populates="bet")
    transactions = relationship("Transaction", back_populates="bet")
    trick_shot_event = relationship("TrickShotEvent", back_populates="bets")


class BetParticipant(Base):
    """Bet participant model"""
    __tablename__ = "bet_participants"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Participant details
    position = Column(String(50), nullable=False)  # "yes", "no", "A", "B", "C", etc.
    amount = Column(Float, nullable=False)
    payout = Column(Float, default=0.0, nullable=False)
    outcome = Column(Enum(BetOutcome), default=BetOutcome.PENDING)

    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bet = relationship("Bet", back_populates="participants")
    user = relationship("User", back_populates="bet_participants")


class TrickShotEvent(Base):
    """Trick shot event model"""
    __tablename__ = "trick_shot_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Streaming details
    stream_url = Column(String(500), nullable=True)
    stream_key = Column(String(255), nullable=True)
    aws_ivs_channel_arn = Column(String(255), nullable=True)

    # Event status
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, live, ended

    # Timestamps
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bets = relationship("Bet", back_populates="trick_shot_event")
