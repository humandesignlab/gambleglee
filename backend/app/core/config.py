"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GambleGlee"
    VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gambleglee:password@localhost:5432/gambleglee"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

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

    # Monitoring
    SENTRY_DSN: Optional[str] = None

    # Compliance
    MINIMUM_AGE: int = 18
    MAX_DEPOSIT_DAILY: float = 1000.0
    MAX_DEPOSIT_WEEKLY: float = 5000.0
    MAX_DEPOSIT_MONTHLY: float = 20000.0

    # Geolocation
    ALLOWED_COUNTRIES: List[str] = ["US"]
    ALLOWED_STATES: List[str] = []  # Empty means all states allowed

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
