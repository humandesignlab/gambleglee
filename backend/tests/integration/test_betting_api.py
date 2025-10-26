"""
Integration tests for betting API endpoints
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient
from fastapi import status

from app.models.betting import BetStatus, BetType, BetOutcome


@pytest.mark.integration
@pytest.mark.financial
class TestBettingAPI:
    """Integration tests for betting API"""

    @pytest.mark.asyncio
    async def test_create_bet_success(self, async_test_client, test_user_token):
        """Test successful bet creation via API"""
        bet_data = {
            "title": "API Test Bet",
            "description": "Test bet via API",
            "bet_type": "friend_bet",
            "amount": 100.0,
            "expires_in_hours": 24,
        }

        response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "API Test Bet"
        assert data["amount"] == 100.0
        assert data["status"] == "pending"
        assert data["bet_type"] == "friend_bet"
        assert "id" in data
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_bet_insufficient_funds(
        self, async_test_client, test_user_token
    ):
        """Test bet creation with insufficient funds"""
        bet_data = {
            "title": "Large Bet",
            "description": "Test large bet",
            "bet_type": "friend_bet",
            "amount": 10000.0,  # Large amount
            "expires_in_hours": 24,
        }

        response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient funds" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_bet_invalid_amount(self, async_test_client, test_user_token):
        """Test bet creation with invalid amount"""
        bet_data = {
            "title": "Invalid Bet",
            "description": "Test invalid amount",
            "bet_type": "friend_bet",
            "amount": -100.0,  # Negative amount
            "expires_in_hours": 24,
        }

        response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_bet_unauthorized(self, async_test_client):
        """Test bet creation without authentication"""
        bet_data = {
            "title": "Unauthorized Bet",
            "description": "Test unauthorized",
            "bet_type": "friend_bet",
            "amount": 100.0,
            "expires_in_hours": 24,
        }

        response = await async_test_client.post("/api/v1/bets/", json=bet_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_accept_bet_success(
        self, async_test_client, test_bet, test_user_2_token
    ):
        """Test successful bet acceptance via API"""
        response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": test_bet.id},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "accepted"
        assert data["id"] == test_bet.id

    @pytest.mark.asyncio
    async def test_accept_bet_not_found(self, async_test_client, test_user_2_token):
        """Test accepting non-existent bet"""
        response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": 99999},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Bet not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_accept_bet_insufficient_funds(
        self, async_test_client, test_bet, test_user_2_token
    ):
        """Test accepting bet with insufficient funds"""
        # Mock insufficient funds scenario
        with patch(
            "app.services.betting_service.BettingService._check_betting_limits"
        ) as mock_check:
            mock_check.side_effect = InsufficientFundsError("Insufficient funds")

            response = await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": test_bet.id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_resolve_bet_success(
        self, async_test_client, test_bet, test_user_token
    ):
        """Test successful bet resolution via API"""
        # Set bet to accepted status first
        test_bet.status = BetStatus.ACCEPTED
        await async_test_client.db.commit()

        resolution_data = {
            "bet_id": test_bet.id,
            "outcome": "winner_a",
            "resolution_data": {"reason": "Test resolution"},
            "resolution_method": "manual",
        }

        response = await async_test_client.post(
            "/api/v1/bets/resolve",
            json=resolution_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "resolved"
        assert data["outcome"] == "winner_a"

    @pytest.mark.asyncio
    async def test_resolve_bet_wrong_status(
        self, async_test_client, test_bet, test_user_token
    ):
        """Test resolving bet with wrong status"""
        resolution_data = {
            "bet_id": test_bet.id,
            "outcome": "winner_a",
            "resolution_data": {"reason": "Test resolution"},
            "resolution_method": "manual",
        }

        response = await async_test_client.post(
            "/api/v1/bets/resolve",
            json=resolution_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Bet cannot be resolved" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_bet_success(
        self, async_test_client, test_bet, test_user_token
    ):
        """Test successful bet cancellation via API"""
        cancel_data = {"bet_id": test_bet.id, "reason": "Test cancellation"}

        response = await async_test_client.post(
            "/api/v1/bets/cancel",
            json=cancel_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["outcome"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_bet_wrong_user(
        self, async_test_client, test_bet, test_user_2_token
    ):
        """Test cancelling bet by wrong user"""
        cancel_data = {"bet_id": test_bet.id, "reason": "Test cancellation"}

        response = await async_test_client.post(
            "/api/v1/bets/cancel",
            json=cancel_data,
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only bet creator can cancel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_bet_success(self, async_test_client, test_bet, test_user_token):
        """Test getting bet by ID via API"""
        response = await async_test_client.get(
            f"/api/v1/bets/{test_bet.id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_bet.id
        assert data["title"] == "Test Bet"

    @pytest.mark.asyncio
    async def test_get_bet_not_found(self, async_test_client, test_user_token):
        """Test getting non-existent bet"""
        response = await async_test_client.get(
            "/api/v1/bets/99999", headers={"Authorization": f"Bearer {test_user_token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_user_bets(self, async_test_client, test_user_token):
        """Test getting user's bets"""
        response = await async_test_client.get(
            "/api/v1/bets/", headers={"Authorization": f"Bearer {test_user_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_get_user_bets_with_status_filter(
        self, async_test_client, test_user_token
    ):
        """Test getting user's bets with status filter"""
        response = await async_test_client.get(
            "/api/v1/bets/?status=pending",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        # All returned bets should have pending status
        for bet in data["items"]:
            assert bet["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_user_bets_pagination(self, async_test_client, test_user_token):
        """Test getting user's bets with pagination"""
        response = await async_test_client.get(
            "/api/v1/bets/?page=1&size=10",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["items"]) <= 10

    @pytest.mark.asyncio
    async def test_get_active_bets_public(self, async_test_client):
        """Test getting active bets without authentication"""
        response = await async_test_client.get("/api/v1/bets/public/active")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        # All returned bets should be active
        for bet in data["items"]:
            assert bet["status"] in ["pending", "accepted", "active"]

    @pytest.mark.asyncio
    async def test_get_bet_statistics(self, async_test_client, test_user_token):
        """Test getting bet statistics"""
        response = await async_test_client.get(
            "/api/v1/bets/statistics",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status_counts" in data
        assert "total_bet_amount" in data
        assert "total_winnings" in data
        assert "net_profit" in data

    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_test_client, test_user_token):
        """Test rate limiting on betting endpoints"""
        bet_data = {
            "title": "Rate Limit Test",
            "description": "Test rate limiting",
            "bet_type": "friend_bet",
            "amount": 100.0,
            "expires_in_hours": 24,
        }

        # Make multiple requests quickly to trigger rate limiting
        responses = []
        for _ in range(15):  # Exceed rate limit of 10/5minute
            response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            responses.append(response)

        # At least one should be rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0

    @pytest.mark.asyncio
    async def test_concurrent_bet_operations(
        self, async_test_client, test_bet, test_user_2_token
    ):
        """Test concurrent bet operations"""
        import asyncio

        async def accept_bet():
            return await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": test_bet.id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )

        # Run concurrent acceptance attempts
        tasks = [accept_bet() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed
        successful_responses = [
            r
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        assert len(successful_responses) <= 1

    @pytest.mark.asyncio
    async def test_bet_workflow_complete(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test complete betting workflow"""
        # 1. Create bet
        bet_data = {
            "title": "Complete Workflow Test",
            "description": "Test complete workflow",
            "bet_type": "friend_bet",
            "amount": 100.0,
            "expires_in_hours": 24,
        }

        create_response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert create_response.status_code == 200
        bet_id = create_response.json()["id"]

        # 2. Accept bet
        accept_response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": bet_id},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["status"] == "accepted"

        # 3. Resolve bet
        resolve_response = await async_test_client.post(
            "/api/v1/bets/resolve",
            json={
                "bet_id": bet_id,
                "outcome": "winner_a",
                "resolution_data": {"reason": "Test resolution"},
                "resolution_method": "manual",
            },
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert resolve_response.status_code == 200
        assert resolve_response.json()["status"] == "resolved"
        assert resolve_response.json()["outcome"] == "winner_a"

    @pytest.mark.asyncio
    async def test_error_handling_validation(self, async_test_client, test_user_token):
        """Test error handling for validation errors"""
        invalid_bet_data = {
            "title": "",  # Empty title
            "description": "Test",
            "bet_type": "invalid_type",  # Invalid bet type
            "amount": 0,  # Invalid amount
            "expires_in_hours": -1,  # Invalid expiration
        }

        response = await async_test_client.post(
            "/api/v1/bets/",
            json=invalid_bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_error_handling_business_logic(
        self, async_test_client, test_bet, test_user_token
    ):
        """Test error handling for business logic errors"""
        # Try to cancel already resolved bet
        test_bet.status = BetStatus.RESOLVED
        await async_test_client.db.commit()

        cancel_data = {"bet_id": test_bet.id, "reason": "Test cancellation"}

        response = await async_test_client.post(
            "/api/v1/bets/cancel",
            json=cancel_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Bet cannot be cancelled" in response.json()["detail"]
