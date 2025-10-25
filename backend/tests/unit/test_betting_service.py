"""
Unit tests for betting service with comprehensive edge case testing
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.services.betting_service import BettingService
from app.models.betting import Bet, BetStatus, BetType, BetOutcome, BetParticipant, BetParticipantRole
from app.models.user import User
from app.models.wallet import Wallet
from app.core.exceptions import ValidationError, InsufficientFundsError, BettingError

@pytest.mark.unit
@pytest.mark.financial
class TestBettingService:
    """Test betting service with comprehensive edge case coverage"""

    @pytest.fixture
    def betting_service(self, test_db_session):
        """Create betting service instance"""
        return BettingService(test_db_session)

    @pytest.fixture
    def mock_wallet_service(self):
        """Mock wallet service"""
        mock_service = AsyncMock()
        mock_service.get_or_create_wallet.return_value = Wallet(
            id=1, user_id=1, balance=Decimal("1000.00"), currency="USD"
        )
        mock_service.lock_funds.return_value = True
        mock_service.unlock_funds.return_value = True
        mock_service.add_funds.return_value = True
        return mock_service

    @pytest.mark.asyncio
    async def test_create_bet_success(self, betting_service, test_user, mock_wallet_service):
        """Test successful bet creation"""
        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            bet = await betting_service.create_bet(
                creator_id=test_user.id,
                title="Test Bet",
                description="Test description",
                bet_type=BetType.FRIEND_BET,
                amount=Decimal("100.00"),
                acceptor_id=None,
                expires_in_hours=24
            )

            assert bet.title == "Test Bet"
            assert bet.amount == Decimal("100.00")
            assert bet.status == BetStatus.PENDING
            assert bet.bet_type == BetType.FRIEND_BET
            assert bet.commission_rate == Decimal("0.05")
            assert bet.commission_amount == Decimal("5.00")
            assert bet.total_pot == Decimal("205.00")
            assert bet.winner_payout == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_bet_insufficient_funds(self, betting_service, test_user):
        """Test bet creation with insufficient funds"""
        mock_wallet = AsyncMock()
        mock_wallet.balance = Decimal("50.00")
        mock_wallet_service = AsyncMock()
        mock_wallet_service.get_or_create_wallet.return_value = mock_wallet

        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            with pytest.raises(InsufficientFundsError):
                await betting_service.create_bet(
                    creator_id=test_user.id,
                    title="Test Bet",
                    description="Test description",
                    bet_type=BetType.FRIEND_BET,
                    amount=Decimal("100.00")
                )

    @pytest.mark.asyncio
    async def test_create_bet_invalid_amount(self, betting_service, test_user):
        """Test bet creation with invalid amount"""
        with pytest.raises(ValidationError, match="Bet amount must be positive"):
            await betting_service.create_bet(
                creator_id=test_user.id,
                title="Test Bet",
                description="Test description",
                bet_type=BetType.FRIEND_BET,
                amount=Decimal("-100.00")
            )

    @pytest.mark.asyncio
    async def test_create_bet_amount_too_small(self, betting_service, test_user):
        """Test bet creation with amount too small"""
        with pytest.raises(ValidationError, match="Minimum bet amount is"):
            await betting_service.create_bet(
                creator_id=test_user.id,
                title="Test Bet",
                description="Test description",
                bet_type=BetType.FRIEND_BET,
                amount=Decimal("0.50")
            )

    @pytest.mark.asyncio
    async def test_create_bet_amount_too_large(self, betting_service, test_user):
        """Test bet creation with amount too large"""
        with pytest.raises(ValidationError, match="Maximum bet amount is"):
            await betting_service.create_bet(
                creator_id=test_user.id,
                title="Test Bet",
                description="Test description",
                bet_type=BetType.FRIEND_BET,
                amount=Decimal("15000.00")
            )

    @pytest.mark.asyncio
    async def test_accept_bet_success(self, betting_service, test_bet, test_user_2, mock_wallet_service):
        """Test successful bet acceptance"""
        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            bet = await betting_service.accept_bet(
                bet_id=test_bet.id,
                acceptor_id=test_user_2.id
            )

            assert bet.status == BetStatus.ACCEPTED
            assert bet.accepted_at is not None
            assert bet.updated_by == test_user_2.id

    @pytest.mark.asyncio
    async def test_accept_bet_not_found(self, betting_service, test_user_2):
        """Test accepting non-existent bet"""
        with pytest.raises(ValidationError, match="Bet not found"):
            await betting_service.accept_bet(
                bet_id=99999,
                acceptor_id=test_user_2.id
            )

    @pytest.mark.asyncio
    async def test_accept_bet_wrong_status(self, betting_service, test_bet, test_user_2):
        """Test accepting bet with wrong status"""
        # Set bet to already accepted
        test_bet.status = BetStatus.ACCEPTED
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet cannot be accepted"):
            await betting_service.accept_bet(
                bet_id=test_bet.id,
                acceptor_id=test_user_2.id
            )

    @pytest.mark.asyncio
    async def test_accept_bet_expired(self, betting_service, test_bet, test_user_2):
        """Test accepting expired bet"""
        # Set bet to expired
        test_bet.expires_at = datetime.utcnow() - timedelta(hours=1)
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet has expired"):
            await betting_service.accept_bet(
                bet_id=test_bet.id,
                acceptor_id=test_user_2.id
            )

    @pytest.mark.asyncio
    async def test_accept_bet_insufficient_funds(self, betting_service, test_bet, test_user_2):
        """Test accepting bet with insufficient funds"""
        mock_wallet = AsyncMock()
        mock_wallet.balance = Decimal("50.00")
        mock_wallet_service = AsyncMock()
        mock_wallet_service.get_or_create_wallet.return_value = mock_wallet

        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            with pytest.raises(InsufficientFundsError):
                await betting_service.accept_bet(
                    bet_id=test_bet.id,
                    acceptor_id=test_user_2.id
                )

    @pytest.mark.asyncio
    async def test_resolve_bet_success(self, betting_service, test_bet, test_user, mock_wallet_service):
        """Test successful bet resolution"""
        # Set bet to accepted status
        test_bet.status = BetStatus.ACCEPTED
        await betting_service.db.commit()

        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            bet = await betting_service.resolve_bet(
                bet_id=test_bet.id,
                outcome=BetOutcome.WINNER_A,
                resolved_by=test_user.id,
                resolution_data={"reason": "Test resolution"}
            )

            assert bet.status == BetStatus.RESOLVED
            assert bet.outcome == BetOutcome.WINNER_A
            assert bet.resolved_at is not None
            assert bet.resolution_method == "manual"

    @pytest.mark.asyncio
    async def test_resolve_bet_wrong_status(self, betting_service, test_bet, test_user):
        """Test resolving bet with wrong status"""
        # Set bet to pending status
        test_bet.status = BetStatus.PENDING
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet cannot be resolved"):
            await betting_service.resolve_bet(
                bet_id=test_bet.id,
                outcome=BetOutcome.WINNER_A,
                resolved_by=test_user.id
            )

    @pytest.mark.asyncio
    async def test_resolve_bet_already_resolved(self, betting_service, test_bet, test_user):
        """Test resolving already resolved bet"""
        # Set bet to resolved status
        test_bet.status = BetStatus.RESOLVED
        test_bet.outcome = BetOutcome.WINNER_A
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet has already been resolved"):
            await betting_service.resolve_bet(
                bet_id=test_bet.id,
                outcome=BetOutcome.WINNER_B,
                resolved_by=test_user.id
            )

    @pytest.mark.asyncio
    async def test_cancel_bet_success(self, betting_service, test_bet, test_user):
        """Test successful bet cancellation"""
        bet = await betting_service.cancel_bet(
            bet_id=test_bet.id,
            user_id=test_user.id,
            reason="Test cancellation"
        )

        assert bet.status == BetStatus.CANCELLED
        assert bet.outcome == BetOutcome.CANCELLED
        assert bet.updated_by == test_user.id

    @pytest.mark.asyncio
    async def test_cancel_bet_wrong_user(self, betting_service, test_bet, test_user_2):
        """Test cancelling bet by wrong user"""
        with pytest.raises(ValidationError, match="Only bet creator can cancel"):
            await betting_service.cancel_bet(
                bet_id=test_bet.id,
                user_id=test_user_2.id,
                reason="Test cancellation"
            )

    @pytest.mark.asyncio
    async def test_cancel_bet_wrong_status(self, betting_service, test_bet, test_user):
        """Test cancelling bet with wrong status"""
        # Set bet to resolved status
        test_bet.status = BetStatus.RESOLVED
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet cannot be cancelled"):
            await betting_service.cancel_bet(
                bet_id=test_bet.id,
                user_id=test_user.id,
                reason="Test cancellation"
            )

    @pytest.mark.asyncio
    async def test_get_bet_success(self, betting_service, test_bet):
        """Test getting bet by ID"""
        bet = await betting_service.get_bet(test_bet.id)

        assert bet is not None
        assert bet.id == test_bet.id
        assert bet.title == "Test Bet"

    @pytest.mark.asyncio
    async def test_get_bet_not_found(self, betting_service):
        """Test getting non-existent bet"""
        bet = await betting_service.get_bet(99999)
        assert bet is None

    @pytest.mark.asyncio
    async def test_get_user_bets(self, betting_service, test_user, test_bet):
        """Test getting user's bets"""
        bets = await betting_service.get_user_bets(
            user_id=test_user.id,
            limit=10,
            offset=0
        )

        assert len(bets) >= 1
        assert any(bet.id == test_bet.id for bet in bets)

    @pytest.mark.asyncio
    async def test_get_user_bets_with_status_filter(self, betting_service, test_user, test_bet):
        """Test getting user's bets with status filter"""
        bets = await betting_service.get_user_bets(
            user_id=test_user.id,
            status=BetStatus.PENDING,
            limit=10,
            offset=0
        )

        assert len(bets) >= 1
        assert all(bet.status == BetStatus.PENDING for bet in bets)

    @pytest.mark.asyncio
    async def test_get_active_bets(self, betting_service, test_bet):
        """Test getting active bets"""
        bets = await betting_service.get_active_bets(limit=10, offset=0)

        assert len(bets) >= 1
        assert any(bet.id == test_bet.id for bet in bets)

    @pytest.mark.asyncio
    async def test_get_bet_statistics(self, betting_service, test_user, test_bet):
        """Test getting bet statistics"""
        stats = await betting_service.get_bet_statistics(test_user.id)

        assert "status_counts" in stats
        assert "total_bet_amount" in stats
        assert "total_winnings" in stats
        assert "net_profit" in stats
        assert stats["total_bet_amount"] >= 100.0

    @pytest.mark.asyncio
    async def test_bet_locking_race_condition(self, betting_service, test_bet, test_user_2):
        """Test bet locking prevents race conditions"""
        # Simulate concurrent bet acceptance
        async def accept_bet():
            try:
                return await betting_service.accept_bet(
                    bet_id=test_bet.id,
                    acceptor_id=test_user_2.id
                )
            except Exception as e:
                return e

        # Run concurrent acceptance attempts
        tasks = [accept_bet() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) <= 1

    @pytest.mark.asyncio
    async def test_commission_calculation_precision(self, betting_service, test_user):
        """Test commission calculation precision"""
        # Test with amount that could cause precision issues
        amount = Decimal("33.33")

        with patch.object(betting_service, 'wallet_service', AsyncMock()):
            bet = await betting_service.create_bet(
                creator_id=test_user.id,
                title="Precision Test",
                description="Test precision",
                bet_type=BetType.FRIEND_BET,
                amount=amount
            )

            # Commission should be 5% of 33.33 = 1.6665, rounded to 1.67
            expected_commission = (amount * Decimal("0.05")).quantize(Decimal("0.01"))
            assert bet.commission_amount == expected_commission
            assert bet.total_pot == amount + bet.commission_amount

    @pytest.mark.asyncio
    async def test_bet_expiration_handling(self, betting_service, test_bet, test_user_2):
        """Test bet expiration handling"""
        # Set bet to expire in the past
        test_bet.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet has expired"):
            await betting_service.accept_bet(
                bet_id=test_bet.id,
                acceptor_id=test_user_2.id
            )

    @pytest.mark.asyncio
    async def test_bet_limit_enforcement(self, betting_service, test_user, test_bet_limit):
        """Test betting limit enforcement"""
        # Test daily limit
        test_bet_limit.daily_bet_amount = Decimal("900.00")  # Close to limit
        await betting_service.db.commit()

        with pytest.raises(ValidationError, match="Bet would exceed daily betting limit"):
            await betting_service.create_bet(
                creator_id=test_user.id,
                title="Limit Test",
                description="Test limits",
                bet_type=BetType.FRIEND_BET,
                amount=Decimal("150.00")  # Would exceed 1000 limit
            )

    @pytest.mark.asyncio
    async def test_fund_distribution_winner_a(self, betting_service, test_bet):
        """Test fund distribution for winner A"""
        # Mock wallet service for fund operations
        mock_wallet_service = AsyncMock()
        mock_wallet_service.unlock_funds.return_value = True
        mock_wallet_service.add_funds.return_value = True

        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            await betting_service._distribute_bet_funds(test_bet, BetOutcome.WINNER_A)

            # Verify fund operations were called
            assert mock_wallet_service.unlock_funds.call_count == 2  # Unlock both stakes
            assert mock_wallet_service.add_funds.call_count == 1  # Add winnings to winner

    @pytest.mark.asyncio
    async def test_fund_distribution_tie(self, betting_service, test_bet):
        """Test fund distribution for tie"""
        mock_wallet_service = AsyncMock()
        mock_wallet_service.unlock_funds.return_value = True
        mock_wallet_service.add_funds.return_value = True

        with patch.object(betting_service, 'wallet_service', mock_wallet_service):
            await betting_service._distribute_bet_funds(test_bet, BetOutcome.TIE)

            # Verify both participants get refunds
            assert mock_wallet_service.unlock_funds.call_count == 2
            assert mock_wallet_service.add_funds.call_count == 2  # Both get refunds

    @pytest.mark.asyncio
    async def test_audit_logging(self, betting_service, test_bet, test_user):
        """Test audit logging functionality"""
        with patch.object(betting_service, '_audit_log') as mock_audit:
            await betting_service.cancel_bet(
                bet_id=test_bet.id,
                user_id=test_user.id,
                reason="Test audit"
            )

            # Verify audit log was called
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args
            assert call_args[0][0] == test_bet.id  # bet_id
            assert call_args[0][1] == test_user.id  # user_id
            assert call_args[0][2] == "bet_cancelled"  # action

    @pytest.mark.asyncio
    async def test_bet_version_optimistic_locking(self, betting_service, test_bet, test_user):
        """Test optimistic locking with version control"""
        # Get initial version
        initial_version = test_bet.version

        # Cancel bet (should increment version)
        await betting_service.cancel_bet(
            bet_id=test_bet.id,
            user_id=test_user.id,
            reason="Version test"
        )

        # Verify version was incremented
        await betting_service.db.refresh(test_bet)
        assert test_bet.version == initial_version + 1

    @pytest.mark.asyncio
    async def test_concurrent_bet_operations(self, betting_service, test_bet, test_user_2):
        """Test concurrent bet operations are handled safely"""
        # Simulate concurrent operations
        async def operation_1():
            try:
                return await betting_service.accept_bet(
                    bet_id=test_bet.id,
                    acceptor_id=test_user_2.id
                )
            except Exception as e:
                return e

        async def operation_2():
            try:
                return await betting_service.cancel_bet(
                    bet_id=test_bet.id,
                    user_id=test_bet.created_by,
                    reason="Concurrent test"
                )
            except Exception as e:
                return e

        # Run operations concurrently
        results = await asyncio.gather(operation_1(), operation_2(), return_exceptions=True)

        # At least one should succeed, and no data corruption should occur
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_operations) >= 1
