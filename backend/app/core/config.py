"""
Application configuration settings
"""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GambleGlee"
    VERSION: str = "1.0.0"
    FRONTEND_URL: str = "http://localhost:3000"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # JWT Settings
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password Security
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 30

    # Two-Factor Authentication
    TWO_FACTOR_ISSUER: str = "GambleGlee"
    TWO_FACTOR_BACKUP_CODES_COUNT: int = 10

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://gambleglee:password@localhost:5432/gambleglee"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # MercadoPago
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    MERCADOPAGO_PUBLIC_KEY: str = ""
    MERCADOPAGO_WEBHOOK_SECRET: str = ""

    # KYC Providers
    PERSONA_API_KEY: str = ""
    PERSONA_ENVIRONMENT: str = "sandbox"
    ONFIDO_API_TOKEN: str = ""
    ONFIDO_WEBHOOK_TOKEN: str = ""

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "gambleglee-assets"
    AWS_IVS_CHANNEL_ARN: str = ""

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # Email Service Settings
    SMTP_USERNAME: str = ""
    FROM_EMAIL: str = "noreply@gambleglee.com"
    FROM_NAME: str = "GambleGlee"

    # Monitoring
    SENTRY_DSN: Optional[str] = None

    # Compliance
    MINIMUM_AGE: int = 18
    MAX_DEPOSIT_DAILY: float = 1000.0
    MAX_DEPOSIT_WEEKLY: float = 5000.0
    MAX_DEPOSIT_MONTHLY: float = 20000.0

    # Geolocation - Mexico and US only
    ALLOWED_COUNTRIES: List[str] = ["US", "MX"]
    ALLOWED_STATES: List[str] = []  # Empty means all states allowed for now

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
