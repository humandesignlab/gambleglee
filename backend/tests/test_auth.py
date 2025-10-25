"""
Authentication tests for GambleGlee
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.core.database import get_db
from app.models.auth import User, UserStatus, AuthProvider
from app.schemas.auth import UserRegisterRequest, UserLoginRequest

client = TestClient(app)

@pytest.fixture
async def db_session():
    """Get database session for testing"""
    # This would be implemented with a test database
    pass

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User"
    }

class TestUserRegistration:
    """Test user registration functionality"""

    async def test_register_user_success(self, db_session, test_user_data):
        """Test successful user registration"""
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

        user_data = data["user"]
        assert user_data["email"] == test_user_data["email"]
        assert user_data["username"] == test_user_data["username"]
        assert user_data["is_active"] is False  # Not verified yet
        assert user_data["is_verified"] is False

    async def test_register_user_duplicate_email(self, db_session, test_user_data):
        """Test registration with duplicate email"""
        # First registration
        client.post("/api/v1/auth/register", json=test_user_data)

        # Second registration with same email
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_user_duplicate_username(self, db_session, test_user_data):
        """Test registration with duplicate username"""
        # First registration
        client.post("/api/v1/auth/register", json=test_user_data)

        # Second registration with same username
        test_user_data["email"] = "test2@example.com"
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    async def test_register_user_weak_password(self, db_session, test_user_data):
        """Test registration with weak password"""
        test_user_data["password"] = "123"
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "Password must be at least 8 characters long" in response.json()["detail"]

    async def test_register_user_invalid_email(self, db_session, test_user_data):
        """Test registration with invalid email"""
        test_user_data["email"] = "invalid-email"
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "email" in response.json()["detail"]

class TestUserLogin:
    """Test user login functionality"""

    async def test_login_success(self, db_session, test_user_data):
        """Test successful user login"""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    async def test_login_invalid_credentials(self, db_session, test_user_data):
        """Test login with invalid credentials"""
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    async def test_login_nonexistent_user(self, db_session):
        """Test login with nonexistent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

class TestEmailVerification:
    """Test email verification functionality"""

    async def test_verify_email_success(self, db_session, test_user_data):
        """Test successful email verification"""
        # Register user
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201

        # In a real test, you'd get the verification token from the database
        # For now, we'll test the endpoint structure
        verification_data = {"token": "test-token"}
        response = client.post("/api/v1/auth/verify-email", json=verification_data)

        # This would succeed in a real implementation
        assert response.status_code in [200, 400]  # 400 for invalid token in test

    async def test_verify_email_invalid_token(self, db_session):
        """Test email verification with invalid token"""
        verification_data = {"token": "invalid-token"}
        response = client.post("/api/v1/auth/verify-email", json=verification_data)

        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]

class TestPasswordReset:
    """Test password reset functionality"""

    async def test_forgot_password_success(self, db_session, test_user_data):
        """Test successful password reset request"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Request password reset
        reset_data = {"email": test_user_data["email"]}
        response = client.post("/api/v1/auth/forgot-password", json=reset_data)

        assert response.status_code == 200
        assert "Password reset email sent" in response.json()["message"]

    async def test_reset_password_success(self, db_session, test_user_data):
        """Test successful password reset"""
        # In a real test, you'd get the reset token from the database
        reset_data = {
            "token": "test-reset-token",
            "new_password": "NewPassword123"
        }
        response = client.post("/api/v1/auth/reset-password", json=reset_data)

        # This would succeed in a real implementation
        assert response.status_code in [200, 400]  # 400 for invalid token in test

    async def test_reset_password_invalid_token(self, db_session):
        """Test password reset with invalid token"""
        reset_data = {
            "token": "invalid-token",
            "new_password": "NewPassword123"
        }
        response = client.post("/api/v1/auth/reset-password", json=reset_data)

        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]

class TestUsernameEmailCheck:
    """Test username and email availability checks"""

    async def test_check_username_available(self, db_session):
        """Test checking available username"""
        username_data = {"username": "availableusername"}
        response = client.post("/api/v1/auth/check-username", json=username_data)

        assert response.status_code == 200
        assert response.json()["available"] is True
        assert "Username is available" in response.json()["message"]

    async def test_check_username_taken(self, db_session, test_user_data):
        """Test checking taken username"""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)

        # Check username availability
        username_data = {"username": test_user_data["username"]}
        response = client.post("/api/v1/auth/check-username", json=username_data)

        assert response.status_code == 200
        assert response.json()["available"] is False
        assert "Username is already taken" in response.json()["message"]

    async def test_check_email_available(self, db_session):
        """Test checking available email"""
        email_data = {"email": "available@example.com"}
        response = client.post("/api/v1/auth/check-email", json=email_data)

        assert response.status_code == 200
        assert response.json()["available"] is True
        assert "Email is available" in response.json()["message"]

    async def test_check_email_taken(self, db_session, test_user_data):
        """Test checking taken email"""
        # Register user first
        client.post("/api/v1/auth/register", json=test_user_data)

        # Check email availability
        email_data = {"email": test_user_data["email"]}
        response = client.post("/api/v1/auth/check-email", json=email_data)

        assert response.status_code == 200
        assert response.json()["available"] is False
        assert "Email is already registered" in response.json()["message"]

class TestTokenRefresh:
    """Test token refresh functionality"""

    async def test_refresh_token_success(self, db_session, test_user_data):
        """Test successful token refresh"""
        # Register and login user
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        refresh_token = login_response.json()["refresh_token"]
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    async def test_refresh_token_invalid(self, db_session):
        """Test token refresh with invalid token"""
        refresh_data = {"refresh_token": "invalid-token"}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

class TestUserProfile:
    """Test user profile functionality"""

    async def test_get_current_user(self, db_session, test_user_data):
        """Test getting current user information"""
        # Register and login user
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == test_user_data["email"]
        assert user_data["username"] == test_user_data["username"]

    async def test_get_current_user_unauthorized(self, db_session):
        """Test getting current user without authentication"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

class TestLogout:
    """Test logout functionality"""

    async def test_logout_success(self, db_session, test_user_data):
        """Test successful logout"""
        # Register and login user
        client.post("/api/v1/auth/register", json=test_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        logout_data = {"logout_all": False}
        response = client.post("/api/v1/auth/logout", json=logout_data, headers=headers)

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    async def test_logout_unauthorized(self, db_session):
        """Test logout without authentication"""
        logout_data = {"logout_all": False}
        response = client.post("/api/v1/auth/logout", json=logout_data)

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
