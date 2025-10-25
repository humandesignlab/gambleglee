"""
User model and related schemas
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class KYCStatus(str, enum.Enum):
    """KYC verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    SELF_EXCLUDED = "self_excluded"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    phone_number = Column(String(20), nullable=True)

    # KYC and verification
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.PENDING)
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_documents = Column(Text, nullable=True)  # JSON string of document IDs

    # Account status
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True)

    # Geolocation
    country = Column(String(2), nullable=True)  # ISO country code
    state = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    created_bets = relationship("Bet", back_populates="creator", foreign_keys="Bet.creator_id")
    bet_participants = relationship("BetParticipant", back_populates="user")
    friendships = relationship("Friendship", back_populates="user", foreign_keys="Friendship.user_id")
    friend_of = relationship("Friendship", back_populates="friend", foreign_keys="Friendship.friend_id")
