"""
Rate limiting functionality for GambleGlee
"""
import asyncio
import time
from typing import Dict, Optional
from functools import wraps
from fastapi import HTTPException, Request, status
import structlog

logger = structlog.get_logger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Clean up old request records"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff_time = current_time - 3600  # 1 hour ago
            
            for key in list(self.requests.keys()):
                self.requests[key] = [
                    req_time for req_time in self.requests[key] 
                    if req_time > cutoff_time
                ]
                if not self.requests[key]:
                    del self.requests[key]
            
            self.last_cleanup = current_time
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed based on rate limit"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean up old requests periodically
        self._cleanup_old_requests()
        
        # Get or create request list for this key
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[key]) < max_requests:
            self.requests[key].append(current_time)
            return True
        
        return False

# Global rate limiter instance
rate_limiter_instance = RateLimiter()

class RateLimitException(Exception):
    """Exception raised when rate limit is exceeded"""
    pass

def rate_limiter(key: str, rate: str):
    """
    Rate limiter decorator
    
    Args:
        key: Unique key for rate limiting (e.g., "create_bet", "user_id")
        rate: Rate limit in format "max_requests/time_window" (e.g., "10/minute", "100/hour")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Parse rate limit
            max_requests, time_window = parse_rate(rate)
            
            # Get rate limit key
            rate_key = get_rate_limit_key(key, args, kwargs)
            
            # Check rate limit
            if not rate_limiter_instance.is_allowed(rate_key, max_requests, time_window):
                logger.warning("Rate limit exceeded", key=rate_key, rate=rate)
                raise RateLimitException(f"Rate limit exceeded: {rate}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def parse_rate(rate: str) -> tuple[int, int]:
    """Parse rate limit string into max_requests and time_window_seconds"""
    try:
        max_requests_str, time_window_str = rate.split('/')
        max_requests = int(max_requests_str)
        
        if time_window_str == 'second':
            time_window = 1
        elif time_window_str == 'minute':
            time_window = 60
        elif time_window_str == 'hour':
            time_window = 3600
        elif time_window_str == 'day':
            time_window = 86400
        else:
            # Assume seconds if no unit specified
            time_window = int(time_window_str)
        
        return max_requests, time_window
    except ValueError:
        raise ValueError(f"Invalid rate format: {rate}. Expected format: 'max_requests/time_window'")

def get_rate_limit_key(key: str, args, kwargs) -> str:
    """Get rate limit key based on the key parameter and function arguments"""
    # Try to get user ID from kwargs (common pattern in FastAPI)
    user_id = kwargs.get('current_user')
    if hasattr(user_id, 'id'):
        user_id = user_id.id
    elif user_id is None:
        user_id = "anonymous"
    
    # Create rate limit key
    if key == "user_id":
        return f"user_{user_id}"
    elif key == "ip_address":
        # Try to get IP from request
        request = kwargs.get('request')
        if request and hasattr(request, 'client'):
            ip = request.client.host if request.client else "unknown"
            return f"ip_{ip}"
        return "ip_unknown"
    else:
        # Use the key as-is
        return f"{key}_{user_id}"

# Rate limiter instance for use in services
rate_limiter = rate_limiter_instance
