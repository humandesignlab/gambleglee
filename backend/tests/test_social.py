"""
Social features tests for GambleGlee
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.core.database import get_db
from app.models.auth import User
from app.models.social import Friendship, UserActivity, Notification
from app.schemas.social import FriendRequestRequest, UserSearchRequest, ActivityCreateRequest

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

@pytest.fixture
def test_friend_data():
    """Test friend data"""
    return {
        "email": "friend@example.com",
        "username": "frienduser",
        "password": "FriendPassword123",
        "first_name": "Friend",
        "last_name": "User",
        "display_name": "Friend User"
    }

class TestFriendSystem:
    """Test friend system functionality"""

    async def test_send_friend_request_success(self, db_session, test_user_data, test_friend_data):
        """Test successful friend request"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Login as first user
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Send friend request
        friend_request = {
            "friend_id": 2,  # Assuming friend has ID 2
            "message": "Let's be friends!"
        }
        response = client.post("/api/v1/social/friends/request", json=friend_request, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["friend_id"] == 2
        assert data["status"] == "pending"
        assert data["initiated_by"] == 1

    async def test_send_friend_request_to_self(self, db_session, test_user_data):
        """Test sending friend request to self"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Send friend request to self
        friend_request = {
            "friend_id": 1,  # Same user ID
            "message": "Let's be friends!"
        }
        response = client.post("/api/v1/social/friends/request", json=friend_request, headers=headers)

        assert response.status_code == 400
        assert "Cannot send friend request to yourself" in response.json()["detail"]

    async def test_accept_friend_request_success(self, db_session, test_user_data, test_friend_data):
        """Test successful friend request acceptance"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send friend request (from previous test)
        # ... (friend request setup)

        # Login as friend
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_friend_data["email"],
            "password": test_friend_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Accept friend request
        friend_response = {
            "friend_id": 1,
            "action": "accept"
        }
        response = client.post("/api/v1/social/friends/respond", json=friend_response, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["accepted_at"] is not None

    async def test_decline_friend_request(self, db_session, test_user_data, test_friend_data):
        """Test declining friend request"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send friend request (from previous test)
        # ... (friend request setup)

        # Login as friend
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_friend_data["email"],
            "password": test_friend_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Decline friend request
        friend_response = {
            "friend_id": 1,
            "action": "decline"
        }
        response = client.post("/api/v1/social/friends/respond", json=friend_response, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "declined"

    async def test_block_user(self, db_session, test_user_data, test_friend_data):
        """Test blocking a user"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Login as first user
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Block user
        response = client.post("/api/v1/social/friends/2/block", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "blocked"
        assert data["user_id"] == 1
        assert data["friend_id"] == 2

    async def test_remove_friend(self, db_session, test_user_data, test_friend_data):
        """Test removing a friend"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send and accept friend request (from previous tests)
        # ... (friendship setup)

        # Login as first user
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Remove friend
        response = client.delete("/api/v1/social/friends/2", headers=headers)

        assert response.status_code == 200
        assert "Friend removed successfully" in response.json()["message"]

    async def test_get_friends_list(self, db_session, test_user_data, test_friend_data):
        """Test getting friends list"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send and accept friend request (from previous tests)
        # ... (friendship setup)

        # Login as first user
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get friends list
        response = client.get("/api/v1/social/friends", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_get_friend_requests(self, db_session, test_user_data, test_friend_data):
        """Test getting friend requests"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send friend request (from previous test)
        # ... (friend request setup)

        # Login as friend
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_friend_data["email"],
            "password": test_friend_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get friend requests
        response = client.get("/api/v1/social/friends/requests", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

class TestUserSearch:
    """Test user search functionality"""

    async def test_search_users_success(self, db_session, test_user_data):
        """Test successful user search"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Search for users
        search_request = {
            "query": "test",
            "search_type": "user",
            "page": 1,
            "size": 10
        }
        response = client.post("/api/v1/social/search/users", json=search_request, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_search_users_with_filters(self, db_session, test_user_data):
        """Test user search with filters"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Search with filters
        search_request = {
            "query": "test",
            "search_type": "user",
            "filters": {
                "location": "New York",
                "min_friends": 0,
                "max_friends": 100,
                "is_online": True
            },
            "page": 1,
            "size": 10
        }
        response = client.post("/api/v1/social/search/users", json=search_request, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

class TestActivityFeed:
    """Test activity feed functionality"""

    async def test_create_activity_success(self, db_session, test_user_data):
        """Test successful activity creation"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Create activity
        activity_request = {
            "activity_type": "bet_created",
            "title": "Created a new bet",
            "description": "I created a bet on the game",
            "is_public": True
        }
        response = client.post("/api/v1/social/activities", json=activity_request, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["activity_type"] == "bet_created"
        assert data["title"] == "Created a new bet"
        assert data["is_public"] is True

    async def test_get_user_activities(self, db_session, test_user_data):
        """Test getting user activities"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Create some activities (from previous test)
        # ... (activity creation)

        # Get user activities
        response = client.get("/api/v1/social/activities", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_get_friends_activities(self, db_session, test_user_data, test_friend_data):
        """Test getting friends' activities"""
        # Register both users
        client.post("/api/v1/auth/register", json=test_user_data)
        client.post("/api/v1/auth/register", json=test_friend_data)

        # Send and accept friend request (from previous tests)
        # ... (friendship setup)

        # Create activities for friend (from previous test)
        # ... (activity creation)

        # Login as first user
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get friends' activities
        response = client.get("/api/v1/social/activities/friends", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

class TestNotifications:
    """Test notification functionality"""

    async def test_get_notifications(self, db_session, test_user_data):
        """Test getting user notifications"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get notifications
        response = client.get("/api/v1/social/notifications", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_mark_notification_read(self, db_session, test_user_data):
        """Test marking notification as read"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Create a notification (from previous tests)
        # ... (notification creation)

        # Mark notification as read
        response = client.post("/api/v1/social/notifications/1/read", headers=headers)

        assert response.status_code == 200
        assert "Notification marked as read" in response.json()["message"]

    async def test_mark_all_notifications_read(self, db_session, test_user_data):
        """Test marking all notifications as read"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Mark all notifications as read
        response = client.post("/api/v1/social/notifications/read-all", headers=headers)

        assert response.status_code == 200
        assert "Marked" in response.json()["message"]
        assert "notifications as read" in response.json()["message"]

class TestLeaderboards:
    """Test leaderboard functionality"""

    async def test_get_leaderboard(self, db_session, test_user_data):
        """Test getting leaderboard"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get leaderboard
        response = client.get("/api/v1/social/leaderboards/betting", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_get_leaderboard_with_time_period(self, db_session, test_user_data):
        """Test getting leaderboard with time period"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get leaderboard with time period
        response = client.get("/api/v1/social/leaderboards/betting?time_period=weekly", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

class TestSocialDashboard:
    """Test social dashboard functionality"""

    async def test_get_social_dashboard(self, db_session, test_user_data):
        """Test getting social dashboard"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get social dashboard
        response = client.get("/api/v1/social/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "user_profile" in data
        assert "recent_activities" in data
        assert "friends_activities" in data
        assert "notifications" in data
        assert "achievements" in data
        assert "leaderboard_position" in data
        assert "stats" in data

class TestErrorHandling:
    """Test error handling in social features"""

    async def test_unauthorized_access(self, db_session):
        """Test unauthorized access to social endpoints"""
        # Try to access social endpoints without authentication
        response = client.get("/api/v1/social/friends")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    async def test_invalid_friend_id(self, db_session, test_user_data):
        """Test invalid friend ID"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to send friend request to non-existent user
        friend_request = {
            "friend_id": 999,  # Non-existent user
            "message": "Let's be friends!"
        }
        response = client.post("/api/v1/social/friends/request", json=friend_request, headers=headers)

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    async def test_invalid_activity_type(self, db_session, test_user_data):
        """Test invalid activity type"""
        # Register user
        client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to create activity with invalid type
        activity_request = {
            "activity_type": "invalid_type",
            "title": "Invalid activity",
            "is_public": True
        }
        response = client.post("/api/v1/social/activities", json=activity_request, headers=headers)

        assert response.status_code == 400
        assert "validation error" in response.json()["detail"].lower()
