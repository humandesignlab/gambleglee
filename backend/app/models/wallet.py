"""
Wallet and transaction models
"""

import enum

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


class TransactionType(str, enum.Enum):
    """Transaction types"""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_PLACED = "bet_placed"
    BET_WON = "bet_won"
    BET_LOST = "bet_lost"
    REFUND = "refund"
    FEE = "fee"


class TransactionStatus(str, enum.Enum):
    """Transaction status"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Wallet(Base):
    """User wallet model"""

    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    locked_balance = Column(Float, default=0.0, nullable=False)  # Funds in escrow
    total_deposited = Column(Float, default=0.0, nullable=False)
    total_withdrawn = Column(Float, default=0.0, nullable=False)
    total_wagered = Column(Float, default=0.0, nullable=False)
    total_won = Column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")


class Transaction(Base):
    """Transaction model"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)

    # Transaction details
    type: Column[TransactionType] = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    status: Column[TransactionStatus] = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    # External references
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_transfer_id = Column(String(255), nullable=True)

    # Related entities
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions")
    bet = relationship("Bet", back_populates="transactions")
