"""
Performance and load testing for GambleGlee betting system
"""

import pytest
import asyncio
import time
from decimal import Decimal
from typing import List, Dict, Any
from httpx import AsyncClient

from app.models.betting import BetStatus, BetType, BetOutcome


@pytest.mark.performance
@pytest.mark.slow
class TestLoadScenarios:
    """Performance tests for betting system under load"""

    @pytest.mark.asyncio
    async def test_concurrent_bet_creation(
        self, async_test_client, test_user_token, performance_test_data
    ):
        """Test concurrent bet creation performance"""

        async def create_bet(bet_id: int):
            bet_data = {
                "title": f"Load Test Bet {bet_id}",
                "description": f"Performance test bet {bet_id}",
                "bet_type": "friend_bet",
                "amount": 50.0 + (bet_id * 10.0),
                "expires_in_hours": 24,
            }

            start_time = time.time()
            response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            end_time = time.time()

            return {
                "bet_id": bet_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200,
            }

        # Create concurrent bet creation tasks
        num_bets = 50
        tasks = [create_bet(i) for i in range(num_bets)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_bets = [
            r for r in results if not isinstance(r, Exception) and r["success"]
        ]
        failed_bets = [
            r for r in results if not isinstance(r, Exception) and not r["success"]
        ]

        # Performance assertions
        assert len(successful_bets) >= num_bets * 0.9  # 90% success rate
        assert total_time < 30.0  # Complete within 30 seconds
        assert len(failed_bets) < num_bets * 0.1  # Less than 10% failures

        # Calculate performance metrics
        avg_response_time = sum(r["response_time"] for r in successful_bets) / len(
            successful_bets
        )
        assert avg_response_time < 2.0  # Average response time under 2 seconds

        print(f"Performance Results:")
        print(f"  Total bets: {num_bets}")
        print(f"  Successful: {len(successful_bets)}")
        print(f"  Failed: {len(failed_bets)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg response time: {avg_response_time:.2f}s")
        print(f"  Bets per second: {num_bets / total_time:.2f}")

    @pytest.mark.asyncio
    async def test_concurrent_bet_acceptance(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test concurrent bet acceptance performance"""

        # Create multiple bets first
        bet_ids = []
        for i in range(20):
            bet_data = {
                "title": f"Acceptance Test Bet {i}",
                "description": f"Test concurrent acceptance {i}",
                "bet_type": "friend_bet",
                "amount": 100.0,
                "expires_in_hours": 24,
            }

            response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )
            if response.status_code == 200:
                bet_ids.append(response.json()["id"])

        async def accept_bet(bet_id: int):
            start_time = time.time()
            response = await async_test_client.post(
                "/api/v1/bets/accept",
                json={"bet_id": bet_id},
                headers={"Authorization": f"Bearer {test_user_2_token}"},
            )
            end_time = time.time()

            return {
                "bet_id": bet_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200,
            }

        # Accept bets concurrently
        tasks = [accept_bet(bet_id) for bet_id in bet_ids]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_acceptances = [
            r for r in results if not isinstance(r, Exception) and r["success"]
        ]

        # Performance assertions
        assert len(successful_acceptances) >= len(bet_ids) * 0.8  # 80% success rate
        assert total_time < 15.0  # Complete within 15 seconds

        print(f"Acceptance Performance Results:")
        print(f"  Total bets: {len(bet_ids)}")
        print(f"  Successful acceptances: {len(successful_acceptances)}")
        print(f"  Total time: {total_time:.2f}s")
        print(
            f"  Acceptances per second: {len(successful_acceptances) / total_time:.2f}"
        )

    @pytest.mark.asyncio
    async def test_database_connection_pooling(
        self, async_test_client, test_user_token
    ):
        """Test database connection pooling under load"""

        async def database_operation(operation_id: int):
            start_time = time.time()

            # Perform database-intensive operation
            response = await async_test_client.get(
                "/api/v1/bets/", headers={"Authorization": f"Bearer {test_user_token}"}
            )

            end_time = time.time()

            return {
                "operation_id": operation_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200,
            }

        # Run many concurrent database operations
        num_operations = 100
        tasks = [database_operation(i) for i in range(num_operations)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_operations = [
            r for r in results if not isinstance(r, Exception) and r["success"]
        ]

        # Performance assertions
        assert len(successful_operations) >= num_operations * 0.95  # 95% success rate
        assert total_time < 20.0  # Complete within 20 seconds

        avg_response_time = sum(
            r["response_time"] for r in successful_operations
        ) / len(successful_operations)
        assert avg_response_time < 1.0  # Average response time under 1 second

        print(f"Database Performance Results:")
        print(f"  Total operations: {num_operations}")
        print(f"  Successful: {len(successful_operations)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg response time: {avg_response_time:.2f}s")
        print(f"  Operations per second: {num_operations / total_time:.2f}")

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, async_test_client, test_user_token):
        """Test memory usage under load"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async def memory_intensive_operation(operation_id: int):
            # Create and process large amounts of data
            bet_data = {
                "title": f"Memory Test Bet {operation_id}",
                "description": "x" * 1000,  # Large description
                "bet_type": "friend_bet",
                "amount": 100.0,
                "expires_in_hours": 24,
                "metadata": {"large_data": "x" * 10000},  # Large metadata
            }

            response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )

            return response.status_code == 200

        # Run memory-intensive operations
        num_operations = 50
        tasks = [memory_intensive_operation(i) for i in range(num_operations)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory assertions
        assert memory_increase < 100  # Memory increase under 100MB
        assert final_memory < 500  # Total memory under 500MB

        successful_operations = [
            r for r in results if not isinstance(r, Exception) and r
        ]
        assert len(successful_operations) >= num_operations * 0.9  # 90% success rate

        print(f"Memory Performance Results:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory increase: {memory_increase:.2f} MB")
        print(f"  Successful operations: {len(successful_operations)}")

    @pytest.mark.asyncio
    async def test_rate_limiting_under_load(self, async_test_client, test_user_token):
        """Test rate limiting under load"""

        async def rate_limit_test():
            bet_data = {
                "title": "Rate Limit Test",
                "description": "Test rate limiting",
                "bet_type": "friend_bet",
                "amount": 100.0,
                "expires_in_hours": 24,
            }

            response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )

            return {
                "status_code": response.status_code,
                "rate_limited": response.status_code == 429,
            }

        # Make many requests quickly to trigger rate limiting
        num_requests = 20
        tasks = [rate_limit_test() for _ in range(num_requests)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_requests = [
            r
            for r in results
            if not isinstance(r, Exception) and r["status_code"] == 200
        ]
        rate_limited_requests = [
            r for r in results if not isinstance(r, Exception) and r["rate_limited"]
        ]

        # Rate limiting assertions
        assert len(rate_limited_requests) > 0  # Some requests should be rate limited
        assert (
            len(successful_requests) < num_requests
        )  # Not all requests should succeed

        print(f"Rate Limiting Results:")
        print(f"  Total requests: {num_requests}")
        print(f"  Successful: {len(successful_requests)}")
        print(f"  Rate limited: {len(rate_limited_requests)}")

    @pytest.mark.asyncio
    async def test_concurrent_bet_resolution(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test concurrent bet resolution performance"""

        # Create and accept multiple bets
        bet_ids = []
        for i in range(10):
            # Create bet
            bet_data = {
                "title": f"Resolution Test Bet {i}",
                "description": f"Test concurrent resolution {i}",
                "bet_type": "friend_bet",
                "amount": 100.0,
                "expires_in_hours": 24,
            }

            create_response = await async_test_client.post(
                "/api/v1/bets/",
                json=bet_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )

            if create_response.status_code == 200:
                bet_id = create_response.json()["id"]

                # Accept bet
                accept_response = await async_test_client.post(
                    "/api/v1/bets/accept",
                    json={"bet_id": bet_id},
                    headers={"Authorization": f"Bearer {test_user_2_token}"},
                )

                if accept_response.status_code == 200:
                    bet_ids.append(bet_id)

        async def resolve_bet(bet_id: int, outcome: str):
            start_time = time.time()

            resolve_data = {
                "bet_id": bet_id,
                "outcome": outcome,
                "resolution_data": {"reason": f"Concurrent resolution test"},
                "resolution_method": "manual",
            }

            response = await async_test_client.post(
                "/api/v1/bets/resolve",
                json=resolve_data,
                headers={"Authorization": f"Bearer {test_user_token}"},
            )

            end_time = time.time()

            return {
                "bet_id": bet_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200,
            }

        # Resolve bets concurrently
        outcomes = ["winner_a", "winner_b", "tie"] * (len(bet_ids) // 3 + 1)
        tasks = [resolve_bet(bet_id, outcomes[i]) for i, bet_id in enumerate(bet_ids)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_resolutions = [
            r for r in results if not isinstance(r, Exception) and r["success"]
        ]

        # Performance assertions
        assert len(successful_resolutions) >= len(bet_ids) * 0.8  # 80% success rate
        assert total_time < 10.0  # Complete within 10 seconds

        avg_response_time = sum(
            r["response_time"] for r in successful_resolutions
        ) / len(successful_resolutions)
        assert avg_response_time < 1.0  # Average response time under 1 second

        print(f"Resolution Performance Results:")
        print(f"  Total bets: {len(bet_ids)}")
        print(f"  Successful resolutions: {len(successful_resolutions)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg response time: {avg_response_time:.2f}s")
        print(
            f"  Resolutions per second: {len(successful_resolutions) / total_time:.2f}"
        )

    @pytest.mark.asyncio
    async def test_stress_testing(
        self, async_test_client, test_user_token, test_user_2_token
    ):
        """Test system under stress conditions"""

        async def stress_operation(operation_id: int):
            try:
                # Create bet
                bet_data = {
                    "title": f"Stress Test Bet {operation_id}",
                    "description": f"Stress test operation {operation_id}",
                    "bet_type": "friend_bet",
                    "amount": 50.0 + (operation_id % 10) * 10.0,
                    "expires_in_hours": 24,
                }

                create_response = await async_test_client.post(
                    "/api/v1/bets/",
                    json=bet_data,
                    headers={"Authorization": f"Bearer {test_user_token}"},
                )

                if create_response.status_code == 200:
                    bet_id = create_response.json()["id"]

                    # Accept bet
                    accept_response = await async_test_client.post(
                        "/api/v1/bets/accept",
                        json={"bet_id": bet_id},
                        headers={"Authorization": f"Bearer {test_user_2_token}"},
                    )

                    if accept_response.status_code == 200:
                        # Resolve bet
                        resolve_data = {
                            "bet_id": bet_id,
                            "outcome": ["winner_a", "winner_b", "tie"][
                                operation_id % 3
                            ],
                            "resolution_data": {
                                "reason": f"Stress test resolution {operation_id}"
                            },
                            "resolution_method": "manual",
                        }

                        resolve_response = await async_test_client.post(
                            "/api/v1/bets/resolve",
                            json=resolve_data,
                            headers={"Authorization": f"Bearer {test_user_token}"},
                        )

                        return resolve_response.status_code == 200

                return False
            except Exception:
                return False

        # Run stress test with many concurrent operations
        num_operations = 100
        tasks = [stress_operation(i) for i in range(num_operations)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_operations = [
            r for r in results if not isinstance(r, Exception) and r
        ]

        # Stress test assertions
        assert (
            len(successful_operations) >= num_operations * 0.7
        )  # 70% success rate under stress
        assert total_time < 60.0  # Complete within 60 seconds

        print(f"Stress Test Results:")
        print(f"  Total operations: {num_operations}")
        print(f"  Successful: {len(successful_operations)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Operations per second: {num_operations / total_time:.2f}")
        print(
            f"  Success rate: {len(successful_operations) / num_operations * 100:.1f}%"
        )
