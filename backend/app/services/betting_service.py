"""
Comprehensive betting service for GambleGlee with extensive edge case handling
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import json
import asyncio
from asyncio import Lock

from app.models.betting import (
    Bet,
    BetStatus,
    BetType,
    BetOutcome,
    BetParticipant,
    BetParticipantRole,
    BetTransaction,
    BetResolution,
    BetAuditLog,
    BetLimit,
)
from app.models.user import User
from app.models.wallet import Transaction, TransactionType, TransactionStatus
from app.core.exceptions import (
    ValidationError,
    InsufficientFundsError,
    BettingError,
    SecurityError,
    BusinessLogicError,
)
from app.services.secure_wallet_service import WalletService as SecureWalletService
import structlog

logger = structlog.get_logger(__name__)


class BettingService:
    """Comprehensive betting service with extensive edge case handling"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = SecureWalletService(db)
        self._bet_locks = {}  # Per-bet locking to prevent race conditions

    async def _get_bet_lock(self, bet_id: int) -> Lock:
        """Get or create a lock for a specific bet to prevent race conditions"""
        if bet_id not in self._bet_locks:
            self._bet_locks[bet_id] = Lock()
        return self._bet_locks[bet_id]

    async def _audit_log(
        self,
        bet_id: int,
        user_id: Optional[int],
        action: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Create audit log entry"""
        audit_entry = BetAuditLog(
            bet_id=bet_id,
            user_id=user_id,
            action=action,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            reason=reason,
            metadata=json.dumps(metadata) if metadata else None,
        )
        self.db.add(audit_entry)
        await self.db.commit()

    # === BET CREATION ===

    async def create_bet(
        self,
        creator_id: int,
        title: str,
        description: str,
        bet_type: BetType,
        amount: Decimal,
        acceptor_id: Optional[int] = None,
        event_id: Optional[int] = None,
        event_type: Optional[str] = None,
        expires_in_hours: int = 24,
        metadata: Optional[Dict] = None,
    ) -> Bet:
        """Create a new bet with comprehensive validation"""

        # Validate inputs
        if amount <= 0:
            raise ValidationError("Bet amount must be positive")

        if amount < Decimal("1.00"):
            raise ValidationError("Minimum bet amount is $1.00")

        if amount > Decimal("10000.00"):
            raise ValidationError("Maximum bet amount is $10,000.00")

        # Check user betting limits
        await self._check_betting_limits(creator_id, amount)

        # Check user has sufficient funds
        user_wallet = await self.wallet_service.get_or_create_wallet(creator_id)
        if user_wallet.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Required: ${amount}, Available: ${user_wallet.balance}"
            )

        # Calculate financial details
        commission_rate = Decimal("0.05")  # 5% commission
        commission_amount = (amount * commission_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_pot = amount + commission_amount
        winner_payout = (
            amount  # Winner gets the bet amount (commission goes to platform)
        )

        # Set expiration time
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        # Create bet
        bet = Bet(
            title=title,
            description=description,
            bet_type=bet_type,
            amount=amount,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            total_pot=total_pot,
            winner_payout=winner_payout,
            expires_at=expires_at,
            event_id=event_id,
            event_type=event_type,
            created_by=creator_id,
            metadata=json.dumps(metadata) if metadata else None,
        )

        self.db.add(bet)
        await self.db.flush()  # Get the ID

        # Create creator participant
        creator_participant = BetParticipant(
            bet_id=bet.id,
            user_id=creator_id,
            role=BetParticipantRole.CREATOR,
            stake_amount=amount,
            potential_winnings=winner_payout,
        )
        self.db.add(creator_participant)

        # Create acceptor participant if specified
        if acceptor_id:
            acceptor_participant = BetParticipant(
                bet_id=bet.id,
                user_id=acceptor_id,
                role=BetParticipantRole.ACCEPTOR,
                stake_amount=amount,
                potential_winnings=winner_payout,
            )
            self.db.add(acceptor_participant)

        await self.db.commit()

        # Audit log
        await self._audit_log(
            bet.id,
            creator_id,
            "bet_created",
            new_value={
                "title": title,
                "amount": float(amount),
                "bet_type": bet_type.value,
            },
        )

        logger.info(
            "Bet created", bet_id=bet.id, creator_id=creator_id, amount=float(amount)
        )

        return bet

    async def _check_betting_limits(self, user_id: int, amount: Decimal) -> None:
        """Check if user has exceeded betting limits"""
        result = await self.db.execute(
            select(BetLimit).where(BetLimit.user_id == user_id)
        )
        bet_limit = result.scalar_one_or_none()

        if not bet_limit:
            # Create default limits for new user
            bet_limit = BetLimit(
                user_id=user_id,
                daily_reset_at=datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                + timedelta(days=1),
                weekly_reset_at=datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                + timedelta(weeks=1),
                monthly_reset_at=datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                + timedelta(days=30),
            )
            self.db.add(bet_limit)
            await self.db.commit()

        # Check if limits need reset
        now = datetime.utcnow()
        if now >= bet_limit.daily_reset_at:
            bet_limit.daily_bet_count = 0
            bet_limit.daily_bet_amount = Decimal("0")
            bet_limit.daily_reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        if now >= bet_limit.weekly_reset_at:
            bet_limit.weekly_bet_count = 0
            bet_limit.weekly_bet_amount = Decimal("0")
            bet_limit.weekly_reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(weeks=1)

        if now >= bet_limit.monthly_reset_at:
            bet_limit.monthly_bet_count = 0
            bet_limit.monthly_bet_amount = Decimal("0")
            bet_limit.monthly_reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=30)

        # Check limits
        if amount > bet_limit.max_single_bet:
            raise ValidationError(
                f"Bet amount exceeds maximum single bet limit of ${bet_limit.max_single_bet}"
            )

        if amount < bet_limit.min_single_bet:
            raise ValidationError(
                f"Bet amount below minimum single bet limit of ${bet_limit.min_single_bet}"
            )

        if bet_limit.daily_bet_amount + amount > bet_limit.daily_bet_limit:
            raise ValidationError(
                f"Bet would exceed daily betting limit of ${bet_limit.daily_bet_limit}"
            )

        if bet_limit.weekly_bet_amount + amount > bet_limit.weekly_bet_limit:
            raise ValidationError(
                f"Bet would exceed weekly betting limit of ${bet_limit.weekly_bet_limit}"
            )

        if bet_limit.monthly_bet_amount + amount > bet_limit.monthly_bet_limit:
            raise ValidationError(
                f"Bet would exceed monthly betting limit of ${bet_limit.monthly_bet_limit}"
            )

        # Update limits
        bet_limit.daily_bet_count += 1
        bet_limit.daily_bet_amount += amount
        bet_limit.weekly_bet_count += 1
        bet_limit.weekly_bet_amount += amount
        bet_limit.monthly_bet_count += 1
        bet_limit.monthly_bet_amount += amount

        await self.db.commit()

    # === BET ACCEPTANCE ===

    async def accept_bet(self, bet_id: int, acceptor_id: int) -> Bet:
        """Accept a bet with comprehensive validation and escrow locking"""

        # Get bet with lock
        bet_lock = await self._get_bet_lock(bet_id)
        async with bet_lock:
            # Get bet with participants
            result = await self.db.execute(
                select(Bet)
                .options(selectinload(Bet.participants))
                .where(Bet.id == bet_id)
            )
            bet = result.scalar_one_or_none()

            if not bet:
                raise ValidationError("Bet not found")

            # Validate bet status
            if bet.status != BetStatus.PENDING:
                raise ValidationError(
                    f"Bet cannot be accepted. Current status: {bet.status.value}"
                )

            # Check if bet has expired
            if bet.expires_at and datetime.utcnow() > bet.expires_at:
                bet.status = BetStatus.EXPIRED
                await self.db.commit()
                raise ValidationError("Bet has expired")

            # Check if user is already a participant
            existing_participant = next(
                (p for p in bet.participants if p.user_id == acceptor_id), None
            )
            if existing_participant:
                raise ValidationError("User is already a participant in this bet")

            # Check acceptor has sufficient funds
            acceptor_wallet = await self.wallet_service.get_or_create_wallet(
                acceptor_id
            )
            if acceptor_wallet.balance < bet.amount:
                raise InsufficientFundsError(
                    f"Insufficient funds. Required: ${bet.amount}, Available: ${acceptor_wallet.balance}"
                )

            # Check acceptor betting limits
            await self._check_betting_limits(acceptor_id, bet.amount)

            # Lock funds for both participants
            try:
                # Lock creator's funds
                await self.wallet_service.lock_funds(
                    bet.created_by,
                    bet.amount,
                    f"Bet {bet.id} - Creator stake",
                    {"bet_id": bet.id, "role": "creator"},
                )

                # Lock acceptor's funds
                await self.wallet_service.lock_funds(
                    acceptor_id,
                    bet.amount,
                    f"Bet {bet.id} - Acceptor stake",
                    {"bet_id": bet.id, "role": "acceptor"},
                )

                # Update bet status
                old_status = bet.status.value
                bet.status = BetStatus.ACCEPTED
                bet.accepted_at = datetime.utcnow()
                bet.updated_by = acceptor_id
                bet.version += 1

                # Update or create acceptor participant
                acceptor_participant = next(
                    (
                        p
                        for p in bet.participants
                        if p.role == BetParticipantRole.ACCEPTOR
                    ),
                    None,
                )
                if acceptor_participant:
                    acceptor_participant.user_id = acceptor_id
                    acceptor_participant.stake_amount = bet.amount
                    acceptor_participant.potential_winnings = bet.winner_payout
                else:
                    acceptor_participant = BetParticipant(
                        bet_id=bet.id,
                        user_id=acceptor_id,
                        role=BetParticipantRole.ACCEPTOR,
                        stake_amount=bet.amount,
                        potential_winnings=bet.winner_payout,
                    )
                    self.db.add(acceptor_participant)

                await self.db.commit()

                # Audit log
                await self._audit_log(
                    bet.id,
                    acceptor_id,
                    "bet_accepted",
                    old_value={"status": old_status},
                    new_value={"status": bet.status.value, "acceptor_id": acceptor_id},
                )

                logger.info("Bet accepted", bet_id=bet.id, acceptor_id=acceptor_id)

                return bet

            except Exception as e:
                # Rollback fund locks if bet acceptance fails
                try:
                    await self.wallet_service.unlock_funds(
                        bet.created_by,
                        bet.amount,
                        f"Bet {bet.id} - Rollback creator stake",
                    )
                    await self.wallet_service.unlock_funds(
                        acceptor_id,
                        bet.amount,
                        f"Bet {bet.id} - Rollback acceptor stake",
                    )
                except Exception as rollback_error:
                    logger.error(
                        "Failed to rollback fund locks",
                        bet_id=bet.id,
                        error=str(rollback_error),
                    )

                raise e

    # === BET RESOLUTION ===

    async def resolve_bet(
        self,
        bet_id: int,
        outcome: BetOutcome,
        resolved_by: int,
        resolution_data: Optional[Dict] = None,
        resolution_method: str = "manual",
    ) -> Bet:
        """Resolve a bet with comprehensive validation and fund distribution"""

        # Get bet with lock
        bet_lock = await self._get_bet_lock(bet_id)
        async with bet_lock:
            # Get bet with participants
            result = await self.db.execute(
                select(Bet)
                .options(selectinload(Bet.participants))
                .where(Bet.id == bet_id)
            )
            bet = result.scalar_one_or_none()

            if not bet:
                raise ValidationError("Bet not found")

            # Validate bet status
            if bet.status not in [
                BetStatus.ACCEPTED,
                BetStatus.ACTIVE,
                BetStatus.COMPLETED,
            ]:
                raise ValidationError(
                    f"Bet cannot be resolved. Current status: {bet.status.value}"
                )

            # Check if already resolved
            if bet.outcome != BetOutcome.PENDING:
                raise ValidationError("Bet has already been resolved")

            # Update bet status and outcome
            old_status = bet.status.value
            old_outcome = bet.outcome.value

            bet.status = BetStatus.RESOLVED
            bet.outcome = outcome
            bet.resolved_at = datetime.utcnow()
            bet.resolution_method = resolution_method
            bet.resolution_data = (
                json.dumps(resolution_data) if resolution_data else None
            )
            bet.updated_by = resolved_by
            bet.version += 1

            # Create resolution record
            resolution = BetResolution(
                bet_id=bet.id,
                resolution_type=resolution_method,
                resolution_data=(
                    json.dumps(resolution_data) if resolution_data else "{}"
                ),
                outcome=outcome,
                resolved_by=resolved_by,
                status="accepted",
            )
            self.db.add(resolution)

            # Distribute funds based on outcome
            await self._distribute_bet_funds(bet, outcome)

            await self.db.commit()

            # Audit log
            await self._audit_log(
                bet.id,
                resolved_by,
                "bet_resolved",
                old_value={"status": old_status, "outcome": old_outcome},
                new_value={"status": bet.status.value, "outcome": outcome.value},
            )

            logger.info(
                "Bet resolved",
                bet_id=bet.id,
                outcome=outcome.value,
                resolved_by=resolved_by,
            )

            return bet

    async def _distribute_bet_funds(self, bet: Bet, outcome: BetOutcome) -> None:
        """Distribute bet funds based on outcome"""

        # Get participants
        creator_participant = next(
            (p for p in bet.participants if p.role == BetParticipantRole.CREATOR), None
        )
        acceptor_participant = next(
            (p for p in bet.participants if p.role == BetParticipantRole.ACCEPTOR), None
        )

        if not creator_participant or not acceptor_participant:
            raise BusinessLogicError("Invalid bet participants")

        # Unlock all funds first
        await self.wallet_service.unlock_funds(
            bet.created_by, bet.amount, f"Bet {bet.id} - Unlock creator stake"
        )
        await self.wallet_service.unlock_funds(
            acceptor_participant.user_id,
            bet.amount,
            f"Bet {bet.id} - Unlock acceptor stake",
        )

        # Distribute based on outcome
        if outcome == BetOutcome.WINNER_A:  # Creator wins
            # Creator gets their stake back + acceptor's stake
            await self.wallet_service.add_funds(
                bet.created_by,
                bet.winner_payout,
                f"Bet {bet.id} - Winner payout",
                {"bet_id": bet.id, "type": "winner_payout"},
            )
            creator_participant.actual_winnings = bet.winner_payout
            acceptor_participant.actual_winnings = Decimal("0")

        elif outcome == BetOutcome.WINNER_B:  # Acceptor wins
            # Acceptor gets their stake back + creator's stake
            await self.wallet_service.add_funds(
                acceptor_participant.user_id,
                bet.winner_payout,
                f"Bet {bet.id} - Winner payout",
                {"bet_id": bet.id, "type": "winner_payout"},
            )
            creator_participant.actual_winnings = Decimal("0")
            acceptor_participant.actual_winnings = bet.winner_payout

        elif outcome == BetOutcome.TIE:  # Tie - refund both
            # Both get their stake back
            await self.wallet_service.add_funds(
                bet.created_by,
                bet.amount,
                f"Bet {bet.id} - Tie refund",
                {"bet_id": bet.id, "type": "tie_refund"},
            )
            await self.wallet_service.add_funds(
                acceptor_participant.user_id,
                bet.amount,
                f"Bet {bet.id} - Tie refund",
                {"bet_id": bet.id, "type": "tie_refund"},
            )
            creator_participant.actual_winnings = bet.amount
            acceptor_participant.actual_winnings = bet.amount

        elif outcome == BetOutcome.CANCELLED:  # Cancelled - refund both
            # Both get their stake back
            await self.wallet_service.add_funds(
                bet.created_by,
                bet.amount,
                f"Bet {bet.id} - Cancellation refund",
                {"bet_id": bet.id, "type": "cancellation_refund"},
            )
            await self.wallet_service.add_funds(
                acceptor_participant.user_id,
                bet.amount,
                f"Bet {bet.id} - Cancellation refund",
                {"bet_id": bet.id, "type": "cancellation_refund"},
            )
            creator_participant.actual_winnings = bet.amount
            acceptor_participant.actual_winnings = bet.amount

        # Platform gets commission
        if outcome in [BetOutcome.WINNER_A, BetOutcome.WINNER_B]:
            await self.wallet_service.add_funds(
                0,
                bet.commission_amount,  # Platform wallet (user_id = 0)
                f"Bet {bet.id} - Commission",
                {"bet_id": bet.id, "type": "commission"},
            )

    # === BET CANCELLATION ===

    async def cancel_bet(self, bet_id: int, user_id: int, reason: str) -> Bet:
        """Cancel a bet with proper fund handling"""

        bet_lock = await self._get_bet_lock(bet_id)
        async with bet_lock:
            result = await self.db.execute(
                select(Bet)
                .options(selectinload(Bet.participants))
                .where(Bet.id == bet_id)
            )
            bet = result.scalar_one_or_none()

            if not bet:
                raise ValidationError("Bet not found")

            # Validate cancellation rights
            if bet.created_by != user_id:
                raise ValidationError("Only bet creator can cancel the bet")

            if bet.status not in [BetStatus.PENDING, BetStatus.ACCEPTED]:
                raise ValidationError(
                    f"Bet cannot be cancelled. Current status: {bet.status.value}"
                )

            # Update bet status
            old_status = bet.status.value
            bet.status = BetStatus.CANCELLED
            bet.outcome = BetOutcome.CANCELLED
            bet.updated_by = user_id
            bet.version += 1

            # Refund funds if bet was accepted
            if bet.status == BetStatus.ACCEPTED:
                await self._distribute_bet_funds(bet, BetOutcome.CANCELLED)

            await self.db.commit()

            # Audit log
            await self._audit_log(
                bet.id,
                user_id,
                "bet_cancelled",
                old_value={"status": old_status},
                new_value={"status": bet.status.value, "reason": reason},
            )

            logger.info("Bet cancelled", bet_id=bet.id, user_id=user_id, reason=reason)

            return bet

    # === BET QUERIES ===

    async def get_bet(self, bet_id: int) -> Optional[Bet]:
        """Get bet by ID with all related data"""
        result = await self.db.execute(
            select(Bet)
            .options(
                selectinload(Bet.participants),
                selectinload(Bet.transactions),
                selectinload(Bet.creator),
            )
            .where(Bet.id == bet_id)
        )
        return result.scalar_one_or_none()

    async def get_user_bets(
        self,
        user_id: int,
        status: Optional[BetStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Bet]:
        """Get user's bets with optional status filter"""
        query = (
            select(Bet)
            .options(selectinload(Bet.participants), selectinload(Bet.creator))
            .where(
                or_(
                    Bet.created_by == user_id,
                    Bet.participants.any(BetParticipant.user_id == user_id),
                )
            )
        )

        if status:
            query = query.where(Bet.status == status)

        query = query.order_by(Bet.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_active_bets(self, limit: int = 50, offset: int = 0) -> List[Bet]:
        """Get active bets for public viewing"""
        result = await self.db.execute(
            select(Bet)
            .options(selectinload(Bet.participants), selectinload(Bet.creator))
            .where(
                Bet.status.in_(
                    [BetStatus.PENDING, BetStatus.ACCEPTED, BetStatus.ACTIVE]
                )
            )
            .order_by(Bet.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    # === BET STATISTICS ===

    async def get_bet_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive betting statistics for user"""

        # Get bet counts by status
        status_counts = await self.db.execute(
            select(Bet.status, func.count(Bet.id))
            .where(
                or_(
                    Bet.created_by == user_id,
                    Bet.participants.any(BetParticipant.user_id == user_id),
                )
            )
            .group_by(Bet.status)
        )
        status_stats = {status.value: count for status, count in status_counts}

        # Get total amounts
        total_bet_amount = await self.db.execute(
            select(func.sum(Bet.amount)).where(
                or_(
                    Bet.created_by == user_id,
                    Bet.participants.any(BetParticipant.user_id == user_id),
                )
            )
        )
        total_amount = total_bet_amount.scalar() or Decimal("0")

        # Get winnings
        total_winnings = await self.db.execute(
            select(func.sum(BetParticipant.actual_winnings)).where(
                BetParticipant.user_id == user_id
            )
        )
        total_wins = total_winnings.scalar() or Decimal("0")

        return {
            "status_counts": status_stats,
            "total_bet_amount": float(total_amount),
            "total_winnings": float(total_wins),
            "net_profit": float(total_wins - total_amount),
        }
