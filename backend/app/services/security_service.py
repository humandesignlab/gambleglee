"""
Security service for GambleGlee
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class SecurityService:
    """Security service for handling security-related operations"""

    def __init__(self):
        self.risk_thresholds = {"low": 0, "medium": 30, "high": 60, "critical": 80}

    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a security event"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
            }

            # Log to structured logger
            logger.info("SECURITY_EVENT", **log_entry)

            # In a real system, this would also:
            # 1. Store in a security events database
            # 2. Send to SIEM system
            # 3. Trigger alerts for critical events
            # 4. Update user risk score

        except Exception as e:
            logger.error("Failed to log security event", error=str(e))

    async def calculate_risk_score(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_type: str = "unknown",
    ) -> int:
        """Calculate risk score for a security event"""
        try:
            risk_score = 0

            # Base risk by event type
            event_risk_scores = {
                "login_success": 0,
                "login_failure": 20,
                "password_reset": 15,
                "email_verification": 5,
                "account_creation": 10,
                "suspicious_activity": 40,
                "multiple_failed_logins": 60,
                "unusual_location": 30,
                "unusual_device": 25,
                "admin_action": 50,
            }

            risk_score += event_risk_scores.get(event_type, 10)

            # IP-based risk factors
            if ip_address:
                # Check for known malicious IPs (simplified)
                if self._is_suspicious_ip(ip_address):
                    risk_score += 30

                # Check for VPN/Proxy usage (simplified)
                if self._is_vpn_or_proxy(ip_address):
                    risk_score += 20

            # User agent risk factors
            if user_agent:
                if self._is_suspicious_user_agent(user_agent):
                    risk_score += 25

                # Check for automated tools
                if self._is_automated_tool(user_agent):
                    risk_score += 35

            # Time-based risk factors
            current_hour = datetime.utcnow().hour
            if current_hour < 6 or current_hour > 22:  # Unusual hours
                risk_score += 15

            # Cap the risk score
            return min(risk_score, 100)

        except Exception as e:
            logger.error("Failed to calculate risk score", error=str(e))
            return 50  # Default to medium risk

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious"""
        # In a real system, this would check against:
        # - Known malicious IP databases
        # - Tor exit nodes
        # - VPN/Proxy services
        # - Geolocation anomalies

        # For now, just check for localhost in production
        if settings.ENVIRONMENT == "production" and ip_address in [
            "127.0.0.1",
            "localhost",
        ]:
            return True

        return False

    def _is_vpn_or_proxy(self, ip_address: str) -> bool:
        """Check if IP is from VPN/Proxy"""
        # In a real system, this would check against:
        # - VPN service IP ranges
        # - Proxy service databases
        # - ASN information

        # For now, just return False
        return False

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        suspicious_patterns = [
            "bot",
            "crawler",
            "spider",
            "scraper",
            "curl",
            "wget",
            "python-requests",
            "sqlmap",
            "nikto",
            "nmap",
        ]

        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)

    def _is_automated_tool(self, user_agent: str) -> bool:
        """Check if user agent is from automated tool"""
        automated_patterns = [
            "selenium",
            "phantomjs",
            "headless",
            "automated",
            "test",
            "script",
        ]

        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in automated_patterns)

    async def detect_brute_force_attempts(
        self, email: str, ip_address: Optional[str] = None
    ) -> bool:
        """Detect brute force login attempts"""
        try:
            # In a real system, this would:
            # 1. Check recent failed login attempts for this email/IP
            # 2. Use rate limiting and exponential backoff
            # 3. Implement account lockout policies
            # 4. Send alerts for suspicious activity

            # For now, just log the attempt
            await self.log_security_event(
                event_type="login_attempt",
                ip_address=ip_address,
                details={"email": email, "type": "brute_force_check"},
            )

            return False  # No brute force detected

        except Exception as e:
            logger.error("Failed to detect brute force attempts", error=str(e))
            return False

    async def detect_account_takeover(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Detect potential account takeover attempts"""
        try:
            # In a real system, this would:
            # 1. Check for unusual login patterns
            # 2. Verify device fingerprinting
            # 3. Check for multiple concurrent sessions
            # 4. Analyze behavioral patterns

            # For now, just log the attempt
            await self.log_security_event(
                event_type="account_takeover_check",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"type": "takeover_detection"},
            )

            return False  # No takeover detected

        except Exception as e:
            logger.error("Failed to detect account takeover", error=str(e))
            return False

    async def generate_device_fingerprint(
        self,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        screen_resolution: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> str:
        """Generate device fingerprint for security tracking"""
        try:
            fingerprint_data = {
                "user_agent": user_agent or "",
                "ip_address": ip_address or "",
                "screen_resolution": screen_resolution or "",
                "timezone": timezone or "",
            }

            # Create hash of fingerprint data
            fingerprint_string = "|".join(fingerprint_data.values())
            fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

            return fingerprint_hash

        except Exception as e:
            logger.error("Failed to generate device fingerprint", error=str(e))
            return ""

    async def validate_session_security(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Validate session security"""
        try:
            # In a real system, this would:
            # 1. Check session expiration
            # 2. Verify IP address hasn't changed significantly
            # 3. Check user agent consistency
            # 4. Validate device fingerprint

            # For now, just log the validation
            await self.log_security_event(
                event_type="session_validation",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": session_id, "type": "security_check"},
            )

            return True  # Session is valid

        except Exception as e:
            logger.error("Failed to validate session security", error=str(e))
            return False

    async def check_rate_limits(
        self, identifier: str, action: str, limit: int, window_seconds: int
    ) -> bool:
        """Check if action is within rate limits"""
        try:
            # In a real system, this would:
            # 1. Use Redis for rate limiting
            # 2. Implement sliding window or token bucket
            # 3. Different limits for different actions
            # 4. Progressive penalties for violations

            # For now, just log the check
            await self.log_security_event(
                event_type="rate_limit_check",
                details={
                    "identifier": identifier,
                    "action": action,
                    "limit": limit,
                    "window_seconds": window_seconds,
                },
            )

            return True  # Within rate limits

        except Exception as e:
            logger.error("Failed to check rate limits", error=str(e))
            return True  # Allow on error

    async def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token"""
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            logger.error("Failed to generate secure token", error=str(e))
            return ""

    async def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage"""
        try:
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception as e:
            logger.error("Failed to hash sensitive data", error=str(e))
            return ""

    async def validate_input_security(self, input_data: str) -> bool:
        """Validate input for security issues"""
        try:
            # Check for common injection patterns
            dangerous_patterns = [
                "<script",
                "javascript:",
                "onload=",
                "onerror=",
                "union select",
                "drop table",
                "delete from",
                "../",
                "..\\",
                "cmd.exe",
                "powershell",
            ]

            input_lower = input_data.lower()
            for pattern in dangerous_patterns:
                if pattern in input_lower:
                    await self.log_security_event(
                        event_type="suspicious_input",
                        details={"pattern": pattern, "input": input_data[:100]},
                    )
                    return False

            return True

        except Exception as e:
            logger.error("Failed to validate input security", error=str(e))
            return False

    async def get_security_recommendations(self, user_id: int) -> List[str]:
        """Get security recommendations for a user"""
        try:
            recommendations = []

            # In a real system, this would analyze:
            # - Password strength
            # - 2FA status
            # - Login patterns
            # - Device security
            # - Account activity

            # For now, return basic recommendations
            recommendations.extend(
                [
                    "Enable two-factor authentication",
                    "Use a strong, unique password",
                    "Review your login history regularly",
                    "Keep your devices updated",
                    "Be cautious with public Wi-Fi",
                ]
            )

            return recommendations

        except Exception as e:
            logger.error("Failed to get security recommendations", error=str(e))
            return []
