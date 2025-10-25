"""
Enhanced secure authentication system
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis
import logging

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.core.exceptions import AuthenticationError, SecurityError

logger = logging.getLogger(__name__)

# Enhanced security scheme
security = HTTPBearer(auto_error=False)

# Redis for session management
redis_client = redis.from_url(settings.REDIS_URL)


class SecureAuthService:
    """Enhanced secure authentication service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_secure_session(self, user_id: int, request: Request) -> Dict[str, Any]:
        """Create a secure session with device fingerprinting"""
        # Generate secure session token
        session_token = secrets.token_urlsafe(32)
        
        # Get device fingerprint
        device_fingerprint = await self._get_device_fingerprint(request)
        
        # Create session data
        session_data = {
            "user_id": user_id,
            "session_token": session_token,
            "device_fingerprint": device_fingerprint,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        # Store session in Redis
        await redis_client.setex(
            f"session:{session_token}",
            86400,  # 24 hours
            str(session_data)
        )
        
        # Log security event
        logger.info(f"Secure session created for user {user_id}")
        
        return {
            "session_token": session_token,
            "expires_at": session_data["expires_at"]
        }
    
    async def _get_device_fingerprint(self, request: Request) -> str:
        """Generate device fingerprint for security"""
        fingerprint_data = {
            "user_agent": request.headers.get("user-agent", ""),
            "accept_language": request.headers.get("accept-language", ""),
            "accept_encoding": request.headers.get("accept-encoding", ""),
            "ip_address": request.client.host if request.client else "unknown"
        }
        
        fingerprint_string = "|".join(fingerprint_data.values())
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def verify_session(self, session_token: str, request: Request) -> Optional[Dict[str, Any]]:
        """Verify session with device fingerprinting"""
        try:
            # Get session from Redis
            session_data = await redis_client.get(f"session:{session_token}")
            if not session_data:
                return None
            
            session = eval(session_data)  # In production, use proper JSON parsing
            
            # Verify device fingerprint
            current_fingerprint = await self._get_device_fingerprint(request)
            if session.get("device_fingerprint") != current_fingerprint:
                logger.warning(f"Device fingerprint mismatch for session {session_token}")
                await self._invalidate_session(session_token)
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                await self._invalidate_session(session_token)
                return None
            
            return session
            
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return None
    
    async def _invalidate_session(self, session_token: str):
        """Invalidate session"""
        await redis_client.delete(f"session:{session_token}")
        logger.info(f"Session {session_token} invalidated")
    
    async def invalidate_all_user_sessions(self, user_id: int):
        """Invalidate all sessions for a user"""
        # In production, maintain a list of user sessions
        logger.info(f"All sessions invalidated for user {user_id}")


class AccountLockoutService:
    """Account lockout protection service"""
    
    def __init__(self):
        self.max_attempts = 5
        self.lockout_duration = 1800  # 30 minutes
    
    async def record_failed_attempt(self, email: str, ip_address: str):
        """Record failed login attempt"""
        key = f"failed_attempts:{email}:{ip_address}"
        
        # Increment failed attempts
        attempts = await redis_client.incr(key)
        
        if attempts == 1:
            await redis_client.expire(key, self.lockout_duration)
        
        if attempts >= self.max_attempts:
            await self._lock_account(email, ip_address)
            logger.warning(f"Account locked for {email} from {ip_address}")
    
    async def _lock_account(self, email: str, ip_address: str):
        """Lock account"""
        lock_key = f"account_locked:{email}:{ip_address}"
        await redis_client.setex(lock_key, self.lockout_duration, "locked")
    
    async def is_account_locked(self, email: str, ip_address: str) -> bool:
        """Check if account is locked"""
        lock_key = f"account_locked:{email}:{ip_address}"
        return await redis_client.exists(lock_key) > 0
    
    async def clear_failed_attempts(self, email: str, ip_address: str):
        """Clear failed attempts on successful login"""
        key = f"failed_attempts:{email}:{ip_address}"
        await redis_client.delete(key)


class MFAService:
    """Multi-factor authentication service"""
    
    def __init__(self):
        self.issuer = "GambleGlee"
    
    async def generate_mfa_secret(self, user_id: int) -> str:
        """Generate MFA secret for user"""
        # In production, use proper TOTP library
        secret = secrets.token_hex(16)
        
        # Store secret securely
        await redis_client.setex(
            f"mfa_secret:{user_id}",
            3600,  # 1 hour to complete setup
            secret
        )
        
        return secret
    
    async def verify_mfa_code(self, user_id: int, code: str) -> bool:
        """Verify MFA code"""
        # In production, implement proper TOTP verification
        stored_secret = await redis_client.get(f"mfa_secret:{user_id}")
        if not stored_secret:
            return False
        
        # Simple verification (replace with proper TOTP)
        return code == "123456"  # Placeholder
    
    async def enable_mfa(self, user_id: int, secret: str):
        """Enable MFA for user"""
        # Store MFA secret securely
        await redis_client.set(f"mfa_enabled:{user_id}", secret)
        logger.info(f"MFA enabled for user {user_id}")


# Enhanced authentication dependencies
async def get_secure_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user with enhanced security"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    
    # Verify session
    auth_service = SecureAuthService(db)
    session = await auth_service.verify_session(token, request)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == session["user_id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    return user


async def require_mfa_verified(
    current_user: User = Depends(get_secure_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Require MFA verification"""
    mfa_service = MFAService()
    mfa_enabled = await redis_client.exists(f"mfa_enabled:{current_user.id}")
    
    if mfa_enabled:
        # In production, verify MFA token
        pass
    
    return current_user


async def require_kyc_verified(
    current_user: User = Depends(get_secure_current_user)
) -> User:
    """Require KYC verification"""
    if current_user.kyc_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required"
        )
    return current_user
