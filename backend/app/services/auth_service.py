"""
Authentication service for GambleGlee
"""

import base64
import io
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode
import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (AccountLockedError, AuthenticationError,
                                 EmailNotVerifiedError, SecurityError,
                                 UserNotFoundError, ValidationError)
from app.models.auth import (AuthProvider, EmailVerification, LoginHistory,
                             PasswordReset, TwoFactorBackup, User, UserDevice,
                             UserRole, UserSession, UserStatus)
from app.schemas.auth import (ChangePasswordRequest, EmailCheckRequest,
                              EmailVerificationRequest, LoginAttempt,
                              LogoutRequest, OAuthLoginRequest,
                              PasswordResetConfirmRequest,
                              PasswordResetRequest, RefreshTokenRequest,
                              SecurityEvent, SessionData, TokenData,
                              TwoFactorDisableRequest, TwoFactorSetupRequest,
                              TwoFactorVerifyRequest, UserLoginRequest,
                              UsernameCheckRequest, UserRegisterRequest)
from app.services.email_service import EmailService
from app.services.security_service import SecurityService

logger = structlog.get_logger(__name__)


class AuthService:
    """Comprehensive authentication service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.email_service = EmailService()
        self.security_service = SecurityService()

    # === PASSWORD MANAGEMENT ===

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    # === USER REGISTRATION ===

    async def register_user(
        self, user_data: UserRegisterRequest, ip_address: Optional[str] = None
    ) -> User:
        """Register a new user"""

        # Check if email already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValidationError("Email already registered")

        # Check if username already exists
        existing_username = await self.get_user_by_username(user_data.username)
        if existing_username:
            raise ValidationError("Username already taken")

        # Create user
        hashed_password = self.get_password_hash(user_data.password)
        email_verification_token = secrets.token_urlsafe(32)

        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            display_name=user_data.display_name or user_data.username,
            email_verification_token=email_verification_token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
            marketing_emails=user_data.marketing_emails,
            auth_provider=AuthProvider.EMAIL,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Send verification email
        await self.email_service.send_verification_email(
            user.email, user.first_name or user.username, email_verification_token
        )

        # Log registration event
        await self.security_service.log_security_event(
            event_type="user_registration",
            user_id=user.id,
            ip_address=ip_address,
            details={"email": user.email, "username": user.username},
        )

        logger.info("User registered", user_id=user.id, email=user.email)
        return user

    # === USER LOGIN ===

    async def login_user(
        self,
        login_data: UserLoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Authenticate user and create session"""

        # Get user
        user = await self.get_user_by_email(login_data.email)
        if not user:
            await self._log_failed_login(login_data.email, ip_address, "user_not_found")
            raise AuthenticationError("Invalid credentials")

        # Check account status
        if user.status == UserStatus.BANNED:
            raise AuthenticationError("Account is banned")

        if user.status == UserStatus.DELETED:
            raise AuthenticationError("Account is deleted")

        if user.locked_until and user.locked_until > datetime.utcnow():
            raise AccountLockedError("Account is temporarily locked")

        # Check if email is verified
        if not user.is_verified:
            raise EmailNotVerifiedError("Email not verified")

        # Verify password
        if not self.verify_password(login_data.password, user.hashed_password):
            await self._handle_failed_login(user, ip_address)
            raise AuthenticationError("Invalid credentials")

        # Check if 2FA is enabled
        if user.two_factor_enabled:
            # For now, we'll require 2FA code in a separate step
            # In a real implementation, you'd handle this in the login flow
            pass

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.locked_until = None

        # Update login tracking
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1

        # Create session
        session = await self._create_user_session(
            user, ip_address, user_agent, login_data.device_name, login_data.device_type
        )

        # Generate tokens
        access_token = await self._create_access_token(user, session.session_id)
        refresh_token = await self._create_refresh_token(user, session.session_id)

        # Log successful login
        await self._log_successful_login(user, ip_address, user_agent, "password")

        await self.db.commit()

        logger.info("User logged in", user_id=user.id, email=user.email)
        return user, access_token, refresh_token

    # === SESSION MANAGEMENT ===

    async def _create_user_session(
        self,
        user: User,
        ip_address: Optional[str],
        user_agent: Optional[str],
        device_name: Optional[str],
        device_type: Optional[str],
    ) -> UserSession:
        """Create a new user session"""

        # Generate session ID
        session_id = secrets.token_urlsafe(32)

        # Create session
        session = UserSession(
            user_id=user.id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            device_type=device_type,
            expires_at=datetime.utcnow() + timedelta(days=30),  # 30 days
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh access token using refresh token"""

        # Verify refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("sub")
            session_id = payload.get("session_id")

            if not user_id or not session_id:
                raise AuthenticationError("Invalid refresh token")

        except JWTError:
            raise AuthenticationError("Invalid refresh token")

        # Get user and session
        user = await self.get_user_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found")

        session = await self.get_session_by_id(session_id)
        if not session or session.status != "active":
            raise AuthenticationError("Invalid session")

        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            raise AuthenticationError("Session expired")

        # Generate new tokens
        new_access_token = await self._create_access_token(user, session_id)
        new_refresh_token = await self._create_refresh_token(user, session_id)

        # Update session activity
        session.last_activity = datetime.utcnow()
        await self.db.commit()

        return new_access_token, new_refresh_token

    async def logout_user(
        self, user_id: int, session_id: Optional[str] = None, logout_all: bool = False
    ) -> int:
        """Logout user from session(s)"""

        if logout_all:
            # Logout from all sessions
            await self.db.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(status="logged_out", revoked_at=datetime.utcnow())
            )
            sessions_logged_out = await self.db.execute(
                select(UserSession).where(UserSession.user_id == user_id)
            )
            count = len(sessions_logged_out.scalars().all())
        else:
            # Logout from specific session
            if session_id:
                await self.db.execute(
                    update(UserSession)
                    .where(
                        and_(
                            UserSession.user_id == user_id,
                            UserSession.session_id == session_id,
                        )
                    )
                    .values(status="logged_out", revoked_at=datetime.utcnow())
                )
                count = 1
            else:
                # Logout from current session (would need to identify current session)
                count = 0

        await self.db.commit()
        return count

    # === TOKEN MANAGEMENT ===

    async def _create_access_token(self, user: User, session_id: str) -> str:
        """Create access token"""
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "session_id": session_id,
            "exp": expire,
            "type": "access",
        }

        return jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    async def _create_refresh_token(self, user: User, session_id: str) -> str:
        """Create refresh token"""
        expires_delta = timedelta(days=30)  # 30 days
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": str(user.id),
            "session_id": session_id,
            "exp": expire,
            "type": "refresh",
        }

        return jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

    # === EMAIL VERIFICATION ===

    async def verify_email(self, token: str) -> User:
        """Verify user email"""

        # Get verification record
        verification = await self.db.execute(
            select(EmailVerification).where(
                and_(
                    EmailVerification.token == token,
                    EmailVerification.is_used == False,
                    EmailVerification.expires_at > datetime.utcnow(),
                )
            )
        )
        verification = verification.scalar_one_or_none()

        if not verification:
            raise ValidationError("Invalid or expired verification token")

        # Get user
        user = await self.get_user_by_id(verification.user_id)
        if not user:
            raise ValidationError("User not found")

        # Update user
        user.is_verified = True
        user.is_active = True
        user.status = UserStatus.ACTIVE
        user.verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_expires = None

        # Mark verification as used
        verification.is_used = True
        verification.used_at = datetime.utcnow()

        await self.db.commit()

        logger.info("Email verified", user_id=user.id, email=user.email)
        return user

    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email"""

        user = await self.get_user_by_email(email)
        if not user:
            raise ValidationError("User not found")

        if user.is_verified:
            raise ValidationError("Email already verified")

        # Generate new token
        token = secrets.token_urlsafe(32)
        user.email_verification_token = token
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)

        await self.db.commit()

        # Send email
        await self.email_service.send_verification_email(
            user.email, user.first_name or user.username, token
        )

        return True

    # === PASSWORD RESET ===

    async def request_password_reset(
        self, email: str, ip_address: Optional[str] = None
    ) -> bool:
        """Request password reset"""

        user = await self.get_user_by_email(email)
        if not user:
            # Don't reveal if user exists
            return True

        # Generate reset token
        token = secrets.token_urlsafe(32)

        # Create password reset record
        password_reset = PasswordReset(
            user_id=user.id,
            token=token,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(hours=1),  # 1 hour expiry
        )

        self.db.add(password_reset)
        await self.db.commit()

        # Send reset email
        await self.email_service.send_password_reset_email(
            user.email, user.first_name or user.username, token
        )

        # Log security event
        await self.security_service.log_security_event(
            event_type="password_reset_requested",
            user_id=user.id,
            ip_address=ip_address,
            details={"email": user.email},
        )

        return True

    async def reset_password(self, token: str, new_password: str) -> User:
        """Reset password using token"""

        # Get reset record
        reset_record = await self.db.execute(
            select(PasswordReset).where(
                and_(
                    PasswordReset.token == token,
                    PasswordReset.is_used == False,
                    PasswordReset.expires_at > datetime.utcnow(),
                )
            )
        )
        reset_record = reset_record.scalar_one_or_none()

        if not reset_record:
            raise ValidationError("Invalid or expired reset token")

        # Get user
        user = await self.get_user_by_id(reset_record.user_id)
        if not user:
            raise ValidationError("User not found")

        # Update password
        user.hashed_password = self.get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None

        # Mark reset as used
        reset_record.is_used = True
        reset_record.used_at = datetime.utcnow()

        # Revoke all sessions
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id)
            .values(status="revoked", revoked_at=datetime.utcnow())
        )

        await self.db.commit()

        logger.info("Password reset", user_id=user.id, email=user.email)
        return user

    # === TWO-FACTOR AUTHENTICATION ===

    async def setup_two_factor(self, user_id: int, password: str) -> Dict[str, str]:
        """Setup two-factor authentication"""

        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValidationError("User not found")

        # Verify password
        if not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid password")

        # Generate secret
        secret = pyotp.random_base32()

        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name="GambleGlee"
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()

        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]

        # Store secret and backup codes (don't enable 2FA yet)
        user.two_factor_secret = secret
        user.backup_codes = ",".join(backup_codes)

        await self.db.commit()

        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code}",
            "backup_codes": backup_codes,
        }

    async def verify_two_factor_setup(self, user_id: int, code: str) -> bool:
        """Verify two-factor setup code"""

        user = await self.get_user_by_id(user_id)
        if not user or not user.two_factor_secret:
            raise ValidationError("2FA not set up")

        # Verify code
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(code, valid_window=1):
            raise ValidationError("Invalid 2FA code")

        # Enable 2FA
        user.two_factor_enabled = True
        await self.db.commit()

        return True

    async def verify_two_factor(
        self, user_id: int, code: str, backup_code: Optional[str] = None
    ) -> bool:
        """Verify two-factor authentication code"""

        user = await self.get_user_by_id(user_id)
        if not user or not user.two_factor_enabled:
            raise ValidationError("2FA not enabled")

        # Try backup code first
        if backup_code and user.backup_codes:
            backup_codes = user.backup_codes.split(",")
            if backup_code in backup_codes:
                # Remove used backup code
                backup_codes.remove(backup_code)
                user.backup_codes = ",".join(backup_codes)
                await self.db.commit()
                return True

        # Try TOTP code
        if user.two_factor_secret:
            totp = pyotp.TOTP(user.two_factor_secret)
            if totp.verify(code, valid_window=1):
                return True

        raise ValidationError("Invalid 2FA code")

    # === USER QUERIES ===

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_session_by_id(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        result = await self.db.execute(
            select(UserSession).where(UserSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    # === UTILITY METHODS ===

    async def _log_failed_login(
        self, email: str, ip_address: Optional[str], reason: str
    ):
        """Log failed login attempt"""
        # This would be implemented to log failed login attempts
        pass

    async def _handle_failed_login(self, user: User, ip_address: Optional[str]):
        """Handle failed login attempt"""
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)

        await self.db.commit()

    async def _log_successful_login(
        self,
        user: User,
        ip_address: Optional[str],
        user_agent: Optional[str],
        login_type: str,
    ):
        """Log successful login"""
        # This would be implemented to log successful logins
        pass

    # === VALIDATION METHODS ===

    async def check_username_availability(self, username: str) -> bool:
        """Check if username is available"""
        user = await self.get_user_by_username(username)
        return user is None

    async def check_email_availability(self, email: str) -> bool:
        """Check if email is available"""
        user = await self.get_user_by_email(email)
        return user is None
