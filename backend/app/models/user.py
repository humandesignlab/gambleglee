"""
User model and related schemas
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


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


# User model moved to app.models.auth.User to avoid duplication
# This file now only contains enums and other user-related models
