"""
Enhanced betting models for GambleGlee with comprehensive edge case handling
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BetStatus(PyEnum):
    """Bet status enumeration"""

    PENDING = "pending"  # Bet created, waiting for acceptance
    ACCEPTED = "accepted"  # Bet accepted, funds locked
    ACTIVE = "active"  # Bet is active and running
    COMPLETED = "completed"  # Bet completed, waiting for resolution
    RESOLVED = "resolved"  # Bet resolved, funds distributed
    CANCELLED = "cancelled"  # Bet cancelled by creator
    EXPIRED = "expired"  # Bet expired without acceptance
    DISPUTED = "disputed"  # Bet under dispute
    REFUNDED = "refunded"  # Bet refunded due to technical issues


class BetType(PyEnum):
    """Bet type enumeration"""

    FRIEND_BET = "friend_bet"  # Bet between friends
    TRICK_SHOT = "trick_shot"  # Bet on trick shot event
    LIVE_EVENT = "live_event"  # Bet on live streaming event
    PREDICTION = "prediction"  # General prediction bet
    CHALLENGE = "challenge"  # Challenge bet
    TOURNAMENT = "tournament"  # Tournament bet


class BetOutcome(PyEnum):
    """Bet outcome enumeration"""

    PENDING = "pending"  # Outcome not yet determined
    WINNER_A = "winner_a"  # User A wins
    WINNER_B = "winner_b"  # User B wins
    TIE = "tie"  # Tie/draw
    CANCELLED = "cancelled"  # Bet cancelled
    DISPUTED = "disputed"  # Outcome disputed


class BetParticipantRole(PyEnum):
    """Bet participant role"""

    CREATOR = "creator"  # User who created the bet
    ACCEPTOR = "acceptor"  # User who accepted the bet
    OBSERVER = "observer"  # User observing the bet
    JUDGE = "judge"  # User judging the outcome


class Bet(Base):
    """Enhanced bet model with comprehensive edge case handling"""

    __tablename__ = "bets"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # Bet details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bet_type: Mapped[BetType] = mapped_column(Enum(BetType), nullable=False)
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus), default=BetStatus.PENDING, nullable=False
    )
    outcome: Mapped[BetOutcome] = mapped_column(
        Enum(BetOutcome), default=BetOutcome.PENDING, nullable=False
    )

    # Financial details (using Decimal for precision)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # Total bet amount
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.05
    )  # 5% commission
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_pot: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # Total pot including commission
    winner_payout: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)  # Amount winner receives

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Expiration time

    # Resolution details
    resolution_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'automatic', 'manual', 'judge', 'community'
    resolution_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON data for resolution
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # Reason for dispute
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Event association
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Associated event ID
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Type of associated event

    # Metadata
    bet_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON metadata
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Version for optimistic locking

    # Audit fields
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at_audit: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at_audit: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator = relationship(
        "User", foreign_keys=[created_by], back_populates="created_bets"
    )
    updater = relationship("User", foreign_keys=[updated_by])
    participants = relationship(
        "BetParticipant", back_populates="bet", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "BetTransaction", back_populates="bet", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_bet_status", "status"),
        Index("idx_bet_type", "bet_type"),
        Index("idx_bet_creator", "created_by"),
        Index("idx_bet_created_at", "created_at"),
        Index("idx_bet_expires_at", "expires_at"),
        Index("idx_bet_event", "event_id", "event_type"),
    )


class BetParticipant(Base):
    """Bet participant model with comprehensive role handling"""

    __tablename__ = "bet_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bet_id: Mapped[int] = mapped_column(Integer, ForeignKey("bets.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    role: Mapped[BetParticipantRole] = mapped_column(Enum(BetParticipantRole), nullable=False)

    # Financial details
    stake_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # Amount user is betting
    potential_winnings: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)  # Potential winnings
    actual_winnings: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)  # Actual winnings received

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    bet_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON metadata

    # Relationships
    bet = relationship("Bet", back_populates="participants")
    user = relationship("User", back_populates="bet_participations")

    # Unique constraint
    __table_args__ = (
        Index("idx_participant_bet_user", "bet_id", "user_id", unique=True),
        Index("idx_participant_user", "user_id"),
        Index("idx_participant_role", "role"),
    )


class BetTransaction(Base):
    """Bet transaction model for financial tracking"""

    __tablename__ = "bet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bet_id: Mapped[int] = mapped_column(Integer, ForeignKey("bets.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Transaction details
    transaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'stake', 'payout', 'refund', 'commission'
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # 'pending', 'completed', 'failed', 'cancelled'
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reference information
    wallet_transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.id"), nullable=True
    )
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # External system reference

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bet_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON metadata

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    bet = relationship("Bet", back_populates="transactions")
    user = relationship("User")
    wallet_transaction = relationship("Transaction")

    # Indexes
    __table_args__ = (
        Index("idx_bet_transaction_bet", "bet_id"),
        Index("idx_bet_transaction_user", "user_id"),
        Index("idx_bet_transaction_type", "transaction_type"),
        Index("idx_bet_transaction_status", "status"),
        Index("idx_bet_transaction_created", "created_at"),
    )


class BetResolution(Base):
    """Bet resolution model for dispute handling"""

    __tablename__ = "bet_resolutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bet_id: Mapped[int] = mapped_column(Integer, ForeignKey("bets.id"), nullable=False, unique=True)

    # Resolution details
    resolution_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'automatic', 'manual', 'judge', 'community'
    resolution_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON resolution data
    outcome: Mapped[BetOutcome] = mapped_column(Enum(BetOutcome), nullable=False)

    # Resolution participants
    resolved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who resolved
    judge_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Judge if applicable

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # 'pending', 'accepted', 'disputed', 'final'
    disputed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who disputed
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    bet = relationship("Bet")
    resolver = relationship("User", foreign_keys=[resolved_by])
    judge = relationship("User", foreign_keys=[judge_id])
    disputer = relationship("User", foreign_keys=[disputed_by])

    # Indexes
    __table_args__ = (
        Index("idx_resolution_bet", "bet_id"),
        Index("idx_resolution_status", "status"),
        Index("idx_resolution_type", "resolution_type"),
        Index("idx_resolution_resolved_at", "resolved_at"),
    )


class BetAuditLog(Base):
    """Bet audit log for comprehensive tracking"""

    __tablename__ = "bet_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bet_id: Mapped[int] = mapped_column(Integer, ForeignKey("bets.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who performed action

    # Audit details
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # Action performed
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)  # Previous value (JSON)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)  # New value (JSON)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # Reason for change

    # Metadata
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IP address
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)  # User agent
    resolution_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # Additional metadata (JSON)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    bet = relationship("Bet")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_audit_bet", "bet_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
    )


class BetLimit(Base):
    """Bet limits model for risk management"""

    __tablename__ = "bet_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Daily limits
    daily_bet_limit = Column(Numeric(15, 2), nullable=False, default=1000)
    daily_bet_count = Column(Integer, default=0, nullable=False)
    daily_bet_amount = Column(Numeric(15, 2), default=0, nullable=False)

    # Weekly limits
    weekly_bet_limit = Column(Numeric(15, 2), nullable=False, default=5000)
    weekly_bet_count = Column(Integer, default=0, nullable=False)
    weekly_bet_amount = Column(Numeric(15, 2), default=0, nullable=False)

    # Monthly limits
    monthly_bet_limit = Column(Numeric(15, 2), nullable=False, default=20000)
    monthly_bet_count = Column(Integer, default=0, nullable=False)
    monthly_bet_amount = Column(Numeric(15, 2), default=0, nullable=False)

    # Single bet limits
    max_single_bet = Column(Numeric(15, 2), nullable=False, default=500)
    min_single_bet = Column(Numeric(15, 2), nullable=False, default=1)

    # Reset tracking
    daily_reset_at = Column(DateTime(timezone=True), nullable=False)
    weekly_reset_at = Column(DateTime(timezone=True), nullable=False)
    monthly_reset_at = Column(DateTime(timezone=True), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
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
    user = relationship("User", back_populates="bet_limits")

    # Indexes
    __table_args__ = (
        Index("idx_bet_limit_user", "user_id"),
        Index("idx_bet_limit_daily_reset", "daily_reset_at"),
        Index("idx_bet_limit_weekly_reset", "weekly_reset_at"),
        Index("idx_bet_limit_monthly_reset", "monthly_reset_at"),
    )
