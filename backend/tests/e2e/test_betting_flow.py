"""
End-to-end tests for complete betting workflows
"""

import pytest
import asyncio
from decimal import Decimal
from httpx import AsyncClient

from app.models.betting import BetStatus, BetOutcome


@pytest.mark.e2e
@pytest.mark.financial
@pytest.mark.slow
class TestBettingFlow:
    """End-to-end tests for betting workflows"""

    @pytest.mark.asyncio
    async def test_complete_betting_workflow(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test complete betting workflow from creation to resolution"""

        # Step 1: Create bet
        bet_data = {
            "title": "E2E Test Bet",
            "description": "Complete workflow test",
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
        bet_data_response = create_response.json()
        bet_id = bet_data_response["id"]

        # Verify bet creation
        assert bet_data_response["title"] == "E2E Test Bet"
        assert bet_data_response["status"] == "pending"
        assert bet_data_response["amount"] == 100.0
        assert bet_data_response["commission_amount"] == 5.0
        assert bet_data_response["total_pot"] == 205.0

        # Step 2: Accept bet
        accept_response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": bet_id},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )
        assert accept_response.status_code == 200
        accept_data = accept_response.json()

        # Verify bet acceptance
        assert accept_data["status"] == "accepted"
        assert accept_data["accepted_at"] is not None

        # Step 3: Resolve bet
        resolve_data = {
            "bet_id": bet_id,
            "outcome": "winner_a",
            "resolution_data": {"reason": "E2E test resolution"},
            "resolution_method": "manual",
        }

        resolve_response = await async_test_client.post(
            "/api/v1/bets/resolve",
            json=resolve_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert resolve_response.status_code == 200
        resolve_data_response = resolve_response.json()

        # Verify bet resolution
        assert resolve_data_response["status"] == "resolved"
        assert resolve_data_response["outcome"] == "winner_a"
        assert resolve_data_response["resolved_at"] is not None

        # Step 4: Verify final state
        get_response = await async_test_client.get(
            f"/api/v1/bets/{bet_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert get_response.status_code == 200
        final_bet = get_response.json()

        assert final_bet["status"] == "resolved"
        assert final_bet["outcome"] == "winner_a"
        assert len(final_bet["participants"]) == 2

        # Verify participants
        creator_participant = next(
            p for p in final_bet["participants"] if p["role"] == "creator"
        )
        acceptor_participant = next(
            p for p in final_bet["participants"] if p["role"] == "acceptor"
        )

        assert creator_participant["actual_winnings"] == 100.0  # Winner gets the pot
        assert acceptor_participant["actual_winnings"] == 0.0  # Loser gets nothing

    @pytest.mark.asyncio
    async def test_bet_cancellation_workflow(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test bet cancellation workflow"""

        # Step 1: Create bet
        bet_data = {
            "title": "Cancellation Test Bet",
            "description": "Test cancellation workflow",
            "bet_type": "friend_bet",
            "amount": 50.0,
            "expires_in_hours": 24,
        }

        create_response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert create_response.status_code == 200
        bet_id = create_response.json()["id"]

        # Step 2: Cancel bet
        cancel_data = {"bet_id": bet_id, "reason": "E2E cancellation test"}

        cancel_response = await async_test_client.post(
            "/api/v1/bets/cancel",
            json=cancel_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert cancel_response.status_code == 200
        cancel_data_response = cancel_response.json()

        # Verify cancellation
        assert cancel_data_response["status"] == "cancelled"
        assert cancel_data_response["outcome"] == "cancelled"

        # Step 3: Verify bet cannot be accepted after cancellation
        accept_response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": bet_id},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )
        assert accept_response.status_code == 400
        assert "Bet cannot be accepted" in accept_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_bet_expiration_workflow(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test bet expiration workflow"""

        # Step 1: Create bet with short expiration
        bet_data = {
            "title": "Expiration Test Bet",
            "description": "Test expiration workflow",
            "bet_type": "friend_bet",
            "amount": 25.0,
            "expires_in_hours": 1,  # Short expiration
        }

        create_response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert create_response.status_code == 200
        bet_id = create_response.json()["id"]

        # Step 2: Wait for expiration (simulate by updating database)
        # In real scenario, this would be handled by a background task
        from app.models.betting import Bet
        from sqlalchemy import update

        # Manually set expiration time to past
        await async_test_client.db.execute(
            update(Bet)
            .where(Bet.id == bet_id)
            .values(
                expires_at=async_test_client.db.execute(
                    "SELECT NOW() - INTERVAL '1 hour'"
                ).scalar()
            )
        )
        await async_test_client.db.commit()

        # Step 3: Try to accept expired bet
        accept_response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": bet_id},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )
        assert accept_response.status_code == 400
        assert "Bet has expired" in accept_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_multi_user_betting_scenario(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test multi-user betting scenario"""

        # User 1 creates multiple bets
        bet_ids = []
        for i in range(3):
            bet_data = {
                "title": f"Multi-user Bet {i+1}",
                "description": f"Test multi-user scenario {i+1}",
                "bet_type": "friend_bet",
                "amount": 50.0 + (i * 25.0),
                "expires_in_hours": 24,
            }

            create_response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert create_response.status_code == 200
            bet_ids.append(create_response.json()["id"])

        # User 2 accepts all bets
        for bet_id in bet_ids:
            accept_response = await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": bet_id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )
            assert accept_response.status_code == 200

        # User 1 resolves all bets with different outcomes
        outcomes = ["winner_a", "winner_b", "tie"]
        for i, bet_id in enumerate(bet_ids):
            resolve_data = {
                "bet_id": bet_id,
                "outcome": outcomes[i],
                "resolution_data": {"reason": f"Multi-user test resolution {i+1}"},
                "resolution_method": "manual",
            }

            resolve_response = await async_test_client.post(
                "/api/v1/bets/resolve",
                json=resolve_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert resolve_response.status_code == 200

        # Verify all bets are resolved
        for bet_id in bet_ids:
            get_response = await async_test_client.get(
                f"/api/v1/bets/{bet_id}",
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert get_response.status_code == 200
            assert get_response.json()["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_betting_limits_enforcement(self, async_test_client, test_user_token):
        """Test betting limits enforcement"""

        # Create bet that would exceed daily limit
        bet_data = {
            "title": "Limit Test Bet",
            "description": "Test betting limits",
            "bet_type": "friend_bet",
            "amount": 2000.0,  # Large amount that might exceed limits
            "expires_in_hours": 24,
        }

        create_response = await async_test_client.post(
            "/api/v1/bets/",
            json=bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        # Should either succeed or fail with limit error
        if create_response.status_code == 400:
            assert "betting limit" in create_response.json()["detail"].lower()
        else:
            assert create_response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_bet_operations(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test concurrent bet operations"""

        # Create bet
        bet_data = {
            "title": "Concurrent Test Bet",
            "description": "Test concurrent operations",
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

        # Run concurrent operations
        async def accept_bet():
            return await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": bet_id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )

        async def cancel_bet():
            return await async_test_client.post(
                "/api/v1/bets/cancel",
                json={"bet_id": bet_id, "reason": "Concurrent test"},
                headers={"Authorization": f"Bearer {test_user_token}"},
            )

        # Run operations concurrently
        results = await asyncio.gather(
            accept_bet(), cancel_bet(), return_exceptions=True
        )

        # At least one should succeed
        successful_operations = [
            r for r in results if not isinstance(r, Exception) and r.status_code == 200
        ]
        assert len(successful_operations) >= 1

        # Verify final state is consistent
        get_response = await async_test_client.get(
            f"/api/v1/bets/{bet_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert get_response.status_code == 200
        final_bet = get_response.json()

        # Bet should be in a valid final state
        assert final_bet["status"] in ["accepted", "cancelled"]

    @pytest.mark.asyncio
    async def test_bet_statistics_tracking(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test bet statistics tracking"""

        # Create and resolve multiple bets
        bet_amounts = [50.0, 100.0, 150.0]
        outcomes = ["winner_a", "winner_b", "tie"]

        for i, (amount, outcome) in enumerate(zip(bet_amounts, outcomes)):
            # Create bet
            bet_data = {
                "title": f"Stats Test Bet {i+1}",
                "description": f"Test statistics tracking {i+1}",
                "bet_type": "friend_bet",
                "amount": amount,
                "expires_in_hours": 24,
            }

            create_response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert create_response.status_code == 200
            bet_id = create_response.json()["id"]

            # Accept bet
            accept_response = await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": bet_id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )
            assert accept_response.status_code == 200

            # Resolve bet
            resolve_data = {
                "bet_id": bet_id,
                "outcome": outcome,
                "resolution_data": {"reason": f"Stats test resolution {i+1}"},
                "resolution_method": "manual",
            }

            resolve_response = await async_test_client.post(
                "/api/v1/bets/resolve",
                json=resolve_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            assert resolve_response.status_code == 200

        # Check statistics
        stats_response = await async_test_client.get(
            "/api/v1/bets/statistics",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Verify statistics
        assert "status_counts" in stats
        assert "total_bet_amount" in stats
        assert "total_winnings" in stats
        assert "net_profit" in stats

        # Total bet amount should be sum of all bets
        expected_total = sum(bet_amounts)
        assert stats["total_bet_amount"] == expected_total

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test error recovery scenarios"""

        # Test invalid bet creation
        invalid_bet_data = {
            "title": "Invalid Bet",
            "description": "Test error handling",
            "bet_type": "friend_bet",
            "amount": -100.0,  # Invalid amount
            "expires_in_hours": 24,
        }

        create_response = await async_test_client.post(
            "/api/v1/bets/",
            json=invalid_bet_data,
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert create_response.status_code == 422  # Validation error

        # Test accepting non-existent bet
        accept_response = await async_test_client.post(
            "/api/v1/bets/accept",
            json={"bet_id": 99999},
            headers={"Authorization": f"Bearer {test_user_2_token}"},
        )
        assert accept_response.status_code == 400
        assert "Bet not found" in accept_response.json()["detail"]

        # Test resolving non-existent bet
        resolve_response = await async_test_client.post(
            "/api/v1/bets/resolve",
            json={
                "bet_id": 99999,
                "outcome": "winner_a",
                "resolution_data": {"reason": "Test error"},
                "resolution_method": "manual",
            },
            headers={"Authorization": f"Bearer {test_user_token}"},
        )
        assert resolve_response.status_code == 400
        assert "Bet not found" in resolve_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authentication_and_authorization(self, async_test_client):
        """Test authentication and authorization"""

        # Test unauthenticated requests
        bet_data = {
            "title": "Unauthorized Bet",
            "description": "Test authentication",
            "bet_type": "friend_bet",
            "amount": 100.0,
            "expires_in_hours": 24,
        }

        create_response = await async_test_client.post("/api/v1/bets/", json=bet_data)
        assert create_response.status_code == 401

        accept_response = await async_test_client.post(
            "/api/v1/bets/accept", json={"bet_id": 1}
        )
        assert accept_response.status_code == 401

        resolve_response = await async_test_client.post(
            "/api/v1/bets/resolve", json={"bet_id": 1, "outcome": "winner_a"}
        )
        assert resolve_response.status_code == 401

        # Test public endpoint (should work without auth)
        public_response = await async_test_client.get("/api/v1/bets/public/active")
        assert public_response.status_code == 200
