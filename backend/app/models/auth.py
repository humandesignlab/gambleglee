"""
Authentication models for GambleGlee
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from datetime import datetime, timedelta
import uuid

Base = declarative_base()

class AuthProvider(PyEnum):
    """Authentication provider enumeration"""
    EMAIL = "email"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"
    GITHUB = "github"

class UserRole(PyEnum):
    """User role enumeration"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class UserStatus(PyEnum):
    """User status enumeration"""
    PENDING = "pending"           # Email not verified
    ACTIVE = "active"            # Active user
    SUSPENDED = "suspended"      # Temporarily suspended
    BANNED = "banned"           # Permanently banned
    DELETED = "deleted"         # Account deleted

class SessionStatus(PyEnum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOGGED_OUT = "logged_out"

class User(Base):
    """Enhanced user model with comprehensive authentication fields"""
    __tablename__ = "users"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Authentication providers
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL, nullable=False)
    external_id = Column(String(255), nullable=True)  # OAuth provider user ID
    
    # Security fields
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    
    # Account verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Privacy and preferences
    privacy_level = Column(String(20), default="public", nullable=False)  # public, friends, private
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    marketing_emails = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    
    # Wallet and betting relationships (from existing models)
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    created_bets = relationship("Bet", foreign_keys="Bet.created_by", back_populates="creator")
    bet_participations = relationship("BetParticipant", back_populates="user")
    bet_limits = relationship("BetLimit", back_populates="user", uselist=False)
    
    # Social relationships
    friendships = relationship("Friendship", back_populates="user", foreign_keys="Friendship.user_id")
    friend_of = relationship("Friendship", back_populates="friend", foreign_keys="Friendship.friend_id")

class UserSession(Base):
    """User session model for session management"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session details
    refresh_token = Column(String(500), nullable=True)
    access_token_jti = Column(String(255), nullable=True)  # JWT ID for token revocation
    
    # Device and location info
    device_id = Column(String(255), nullable=True)
    device_name = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Session status
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class LoginHistory(Base):
    """Login history model for security auditing"""
    __tablename__ = "login_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Login details
    login_type = Column(String(50), nullable=False)  # password, oauth, magic_link
    auth_provider = Column(Enum(AuthProvider), nullable=True)
    success = Column(Boolean, nullable=False)
    
    # Device and location info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Security details
    two_factor_used = Column(Boolean, default=False, nullable=False)
    risk_score = Column(Integer, nullable=True)  # 0-100 risk assessment
    
    # Failure details
    failure_reason = Column(String(100), nullable=True)  # wrong_password, account_locked, etc.
    
    # Timestamps
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="login_history")

class UserDevice(Base):
    """User device model for device management"""
    __tablename__ = "user_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Device details
    device_name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)  # mobile, desktop, tablet
    os_name = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)
    browser_name = Column(String(50), nullable=True)
    browser_version = Column(String(50), nullable=True)
    
    # Security
    is_trusted = Column(Boolean, default=False, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="devices")

class EmailVerification(Base):
    """Email verification model"""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Verification details
    token = Column(String(255), unique=True, nullable=False, index=True)
    verification_type = Column(String(50), nullable=False)  # email_verification, password_reset, etc.
    
    # Status
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User")

class PasswordReset(Base):
    """Password reset model"""
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Reset details
    token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Status
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User")

class TwoFactorBackup(Base):
    """Two-factor authentication backup codes model"""
    __tablename__ = "two_factor_backups"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Backup details
    code = Column(String(20), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User")
