"""
Pytest configuration and fixtures for GambleGlee testing
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
import os
import tempfile
import shutil

from app.core.database import get_db, Base
from app.core.config import settings
from app.main import app
from app.models.user import User
from app.models.wallet import Wallet
from app.models.betting import Bet, BetParticipant, BetLimit
from app.core.security import create_access_token, get_password_hash
from app.services.betting_service import BettingService
from app.services.secure_wallet_service import WalletService as SecureWalletService
from app.services.rewards_service import RewardsService

# Test database configuration
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_gambleglee"
TEST_REDIS_URL = "redis://localhost:6379/0"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing"""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for testing"""
    with RedisContainer("redis:7") as redis:
        yield redis


@pytest.fixture(scope="session")
async def test_engine(postgres_container):
    """Create test database engine"""
    database_url = f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}/{postgres_container.dbname}"

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_client(test_db_session):
    """Create test client with database dependency override"""

    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_test_client(test_db_session):
    """Create async test client"""

    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# === USER FIXTURES ===


@pytest.fixture
async def test_user(test_db_session) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(test_db_session) -> User:
    """Create second test user"""
    user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User2",
        is_active=True,
        is_verified=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user) -> str:
    """Create JWT token for test user"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def test_user_2_token(test_user_2) -> str:
    """Create JWT token for second test user"""
    return create_access_token(data={"sub": str(test_user_2.id)})


# === WALLET FIXTURES ===


@pytest.fixture
async def test_wallet(test_db_session, test_user) -> Wallet:
    """Create test wallet for user"""
    wallet = Wallet(user_id=test_user.id, balance=1000.00, currency="USD")
    test_db_session.add(wallet)
    await test_db_session.commit()
    await test_db_session.refresh(wallet)
    return wallet


@pytest.fixture
async def test_wallet_2(test_db_session, test_user_2) -> Wallet:
    """Create test wallet for second user"""
    wallet = Wallet(user_id=test_user_2.id, balance=1000.00, currency="USD")
    test_db_session.add(wallet)
    await test_db_session.commit()
    await test_db_session.refresh(wallet)
    return wallet


# === BETTING FIXTURES ===


@pytest.fixture
async def test_bet(test_db_session, test_user, test_user_2) -> Bet:
    """Create test bet"""
    from decimal import Decimal

    bet = Bet(
        title="Test Bet",
        description="Test bet description",
        bet_type="friend_bet",
        amount=Decimal("100.00"),
        commission_rate=Decimal("0.05"),
        commission_amount=Decimal("5.00"),
        total_pot=Decimal("205.00"),
        winner_payout=Decimal("100.00"),
        created_by=test_user.id,
        status="pending",
    )
    test_db_session.add(bet)
    await test_db_session.commit()
    await test_db_session.refresh(bet)

    # Create participants
    creator_participant = BetParticipant(
        bet_id=bet.id,
        user_id=test_user.id,
        role="creator",
        stake_amount=Decimal("100.00"),
        potential_winnings=Decimal("100.00"),
    )
    test_db_session.add(creator_participant)

    acceptor_participant = BetParticipant(
        bet_id=bet.id,
        user_id=test_user_2.id,
        role="acceptor",
        stake_amount=Decimal("100.00"),
        potential_winnings=Decimal("100.00"),
    )
    test_db_session.add(acceptor_participant)

    await test_db_session.commit()
    return bet


@pytest.fixture
async def test_bet_limit(test_db_session, test_user) -> BetLimit:
    """Create test bet limit for user"""
    from datetime import datetime, timedelta

    bet_limit = BetLimit(
        user_id=test_user.id,
        daily_bet_limit=Decimal("1000.00"),
        weekly_bet_limit=Decimal("5000.00"),
        monthly_bet_limit=Decimal("20000.00"),
        max_single_bet=Decimal("500.00"),
        min_single_bet=Decimal("1.00"),
        daily_reset_at=datetime.utcnow() + timedelta(days=1),
        weekly_reset_at=datetime.utcnow() + timedelta(weeks=1),
        monthly_reset_at=datetime.utcnow() + timedelta(days=30),
    )
    test_db_session.add(bet_limit)
    await test_db_session.commit()
    await test_db_session.refresh(bet_limit)
    return bet_limit


# === SERVICE FIXTURES ===


@pytest.fixture
def betting_service(test_db_session) -> BettingService:
    """Create betting service instance"""
    return BettingService(test_db_session)


@pytest.fixture
def wallet_service(test_db_session) -> SecureWalletService:
    """Create wallet service instance"""
    return SecureWalletService(test_db_session)


@pytest.fixture
def rewards_service(test_db_session) -> RewardsService:
    """Create rewards service instance"""
    return RewardsService(test_db_session)


# === TEST DATA FIXTURES ===


@pytest.fixture
def sample_bet_data():
    """Sample bet creation data"""
    return {
        "title": "Test Bet",
        "description": "Test bet description",
        "bet_type": "friend_bet",
        "amount": 100.0,
        "expires_in_hours": 24,
    }


@pytest.fixture
def sample_bet_resolution_data():
    """Sample bet resolution data"""
    return {
        "outcome": "winner_a",
        "resolution_data": {"reason": "Test resolution"},
        "resolution_method": "manual",
    }


@pytest.fixture
def sample_wallet_data():
    """Sample wallet data"""
    return {"balance": 1000.0, "currency": "USD"}


# === MOCK FIXTURES ===


@pytest.fixture
def mock_stripe_service():
    """Mock Stripe service"""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.create_payment_intent.return_value = {
        "client_secret": "pi_test_123",
        "payment_intent_id": "pi_test_123",
    }
    mock_service.confirm_payment_intent.return_value = {"status": "succeeded"}
    return mock_service


@pytest.fixture
def mock_mercadopago_service():
    """Mock MercadoPago service"""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.create_preference.return_value = {
        "id": "pref_test_123",
        "init_point": "https://test.mercadopago.com/checkout",
    }
    return mock_service


@pytest.fixture
def mock_geolocation_service():
    """Mock geolocation service"""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.get_location_data.return_value = {
        "country": "US",
        "region": "California",
        "city": "San Francisco",
        "compliance_status": "allowed",
        "payment_processor": "stripe",
    }
    return mock_service


# === PERFORMANCE TEST FIXTURES ===


@pytest.fixture
def performance_test_data():
    """Performance test data"""
    return {
        "concurrent_users": 100,
        "bets_per_user": 10,
        "test_duration": 300,  # 5 minutes
        "ramp_up_time": 60,  # 1 minute
    }


# === CLEANUP FIXTURES ===


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_db_session):
    """Cleanup test data after each test"""
    yield
    # Cleanup is handled by database rollback in test_db_session fixture


# === TEST CONFIGURATION ===


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "financial: mark test as financial test")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "slow: mark test as slow test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Mark slow tests
        if "performance" in item.nodeid or "e2e" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Mark financial tests
        if (
            "financial" in item.nodeid
            or "wallet" in item.nodeid
            or "betting" in item.nodeid
        ):
            item.add_marker(pytest.mark.financial)

        # Mark security tests
        if "security" in item.nodeid or "auth" in item.nodeid:
            item.add_marker(pytest.mark.security)
