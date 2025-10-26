"""
Authentication schemas for GambleGlee
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class AuthProvider(str, Enum):
    """Authentication provider enumeration"""

    EMAIL = "email"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"
    GITHUB = "github"


class UserRole(str, Enum):
    """User role enumeration"""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User status enumeration"""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"


# === REQUEST SCHEMAS ===


class UserRegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    display_name: Optional[str] = Field(
        None, max_length=100, description="Display name"
    )
    marketing_emails: bool = Field(False, description="Subscribe to marketing emails")

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError("Username must contain only letters and numbers")
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    """User login request"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember me for longer session")
    device_name: Optional[str] = Field(None, max_length=100, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request"""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )

    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class EmailVerificationRequest(BaseModel):
    """Email verification request"""

    token: str = Field(..., description="Verification token")


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )

    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class TwoFactorSetupRequest(BaseModel):
    """Two-factor authentication setup request"""

    password: str = Field(..., description="Current password")


class TwoFactorVerifyRequest(BaseModel):
    """Two-factor authentication verification request"""

    code: str = Field(..., min_length=6, max_length=6, description="2FA code")
    backup_code: Optional[str] = Field(None, description="Backup code")


class TwoFactorDisableRequest(BaseModel):
    """Two-factor authentication disable request"""

    password: str = Field(..., description="Current password")
    code: str = Field(..., min_length=6, max_length=6, description="2FA code")


class OAuthLoginRequest(BaseModel):
    """OAuth login request"""

    provider: AuthProvider = Field(..., description="OAuth provider")
    code: str = Field(..., description="OAuth authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")
    device_name: Optional[str] = Field(None, max_length=100, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request"""

    session_id: Optional[str] = Field(None, description="Session ID to logout")
    logout_all: bool = Field(False, description="Logout from all devices")


# === RESPONSE SCHEMAS ===


class UserResponse(BaseModel):
    """User response schema"""

    id: int
    uuid: str
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    role: UserRole
    status: UserStatus
    auth_provider: AuthProvider
    two_factor_enabled: bool
    privacy_level: str
    email_notifications: bool
    push_notifications: bool
    marketing_emails: bool
    created_at: datetime
    updated_at: datetime
    verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    login_count: int

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response schema"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class SessionResponse(BaseModel):
    """Session response schema"""

    id: int
    session_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    ip_address: Optional[str]
    location: Optional[str]
    is_current: bool
    created_at: datetime
    last_activity: datetime
    expires_at: datetime


class LoginHistoryResponse(BaseModel):
    """Login history response schema"""

    id: int
    login_type: str
    auth_provider: Optional[AuthProvider]
    success: bool
    ip_address: Optional[str]
    user_agent: Optional[str]
    location: Optional[str]
    two_factor_used: bool
    risk_score: Optional[int]
    failure_reason: Optional[str]
    attempted_at: datetime


class DeviceResponse(BaseModel):
    """Device response schema"""

    id: int
    device_id: str
    device_name: str
    device_type: str
    os_name: Optional[str]
    os_version: Optional[str]
    browser_name: Optional[str]
    browser_version: Optional[str]
    is_trusted: bool
    is_current: bool
    last_used: datetime
    created_at: datetime


class TwoFactorSetupResponse(BaseModel):
    """Two-factor setup response schema"""

    secret: str
    qr_code: str
    backup_codes: List[str]


class PasswordResetResponse(BaseModel):
    """Password reset response schema"""

    message: str
    expires_in: int


class EmailVerificationResponse(BaseModel):
    """Email verification response schema"""

    message: str
    expires_in: int


class LogoutResponse(BaseModel):
    """Logout response schema"""

    message: str
    sessions_logged_out: int


# === INTERNAL SCHEMAS ===


class TokenData(BaseModel):
    """Token data schema for JWT"""

    user_id: int
    email: str
    username: str
    role: UserRole
    session_id: Optional[str] = None
    jti: Optional[str] = None  # JWT ID for token revocation


class SessionData(BaseModel):
    """Session data schema"""

    session_id: str
    user_id: int
    device_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool
    expires_at: datetime


class LoginAttempt(BaseModel):
    """Login attempt schema"""

    email: str
    password: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_fingerprint: Optional[str]
    location: Optional[str]


class SecurityEvent(BaseModel):
    """Security event schema"""

    event_type: str
    user_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]
    risk_score: Optional[int]
    timestamp: datetime


# === VALIDATION SCHEMAS ===


class UsernameCheckRequest(BaseModel):
    """Username availability check request"""

    username: str = Field(..., min_length=3, max_length=50)

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError("Username must contain only letters and numbers")
        return v.lower()


class EmailCheckRequest(BaseModel):
    """Email availability check request"""

    email: EmailStr


class UsernameCheckResponse(BaseModel):
    """Username availability check response"""

    available: bool
    message: Optional[str] = None


class EmailCheckResponse(BaseModel):
    """Email availability check response"""

    available: bool
    message: Optional[str] = None
