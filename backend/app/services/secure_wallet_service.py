"""
Secure wallet service with comprehensive security measures
"""

from typing import Optional, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
import asyncio
import json
import logging
from datetime import datetime, timedelta

from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.services.stripe_service import StripeService
from app.services.mercadopago_service import MercadoPagoService
from app.core.exceptions import InsufficientFundsError, ValidationError, SecurityError

logger = logging.getLogger(__name__)


class SecureWalletService:
    """Secure wallet service with comprehensive security measures"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stripe_service = StripeService()
        self.mercadopago_service = MercadoPagoService()
        self._locks = {}  # Per-user locks to prevent race conditions

    async def _get_user_lock(self, user_id: int):
        """Get or create a lock for a specific user"""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def _validate_amount(self, amount: float) -> Decimal:
        """Validate and normalize amount to prevent precision errors"""
        if amount <= 0:
            raise ValidationError("Amount must be positive")
        if amount > 1000000:  # Max amount limit
            raise ValidationError("Amount exceeds maximum limit")

        # Convert to Decimal for precise arithmetic
        return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    async def _validate_user_ownership(self, user_id: int, current_user_id: int):
        """Validate that the user can only access their own wallet"""
        if user_id != current_user_id:
            raise SecurityError("Access denied: Cannot access other user's wallet")

    async def _check_daily_limits(self, user_id: int, amount: Decimal, transaction_type: TransactionType):
        """Check daily transaction limits"""
        today = datetime.utcnow().date()

        # Get today's transaction total
        result = await self.db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == transaction_type)
            .where(func.date(Transaction.created_at) == today)
            .where(Transaction.status == TransactionStatus.COMPLETED)
        )

        daily_total = result.scalar() or Decimal('0')

        # Check limits based on transaction type
        if transaction_type == TransactionType.DEPOSIT:
            daily_limit = Decimal('1000.00')  # $1000 daily deposit limit
        elif transaction_type == TransactionType.WITHDRAWAL:
            daily_limit = Decimal('5000.00')  # $5000 daily withdrawal limit
        else:
            daily_limit = Decimal('10000.00')  # Default limit

        if daily_total + amount > daily_limit:
            raise ValidationError(f"Daily limit exceeded. Current: ${daily_total}, Limit: ${daily_limit}")

    async def _atomic_balance_update(self, wallet_id: int, amount_change: Decimal,
                                   locked_change: Decimal = Decimal('0')) -> bool:
        """Atomically update wallet balance with row-level locking"""
        try:
            # Use database-level locking and atomic update
            result = await self.db.execute(
                text("""
                    UPDATE wallets
                    SET balance = balance + :amount_change,
                        locked_balance = locked_balance + :locked_change,
                        updated_at = NOW()
                    WHERE id = :wallet_id
                    AND balance + :amount_change >= 0
                    AND locked_balance + :locked_change >= 0
                    RETURNING id
                """),
                {
                    "wallet_id": wallet_id,
                    "amount_change": float(amount_change),
                    "locked_change": float(locked_change)
                }
            )

            if result.rowcount == 0:
                return False  # Update failed (insufficient funds or wallet not found)

            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Atomic balance update failed: {e}")
            raise SecurityError("Failed to update balance atomically")

    async def get_or_create_wallet(self, user_id: int, current_user_id: int) -> Wallet:
        """Get or create user wallet with ownership validation"""
        await self._validate_user_ownership(user_id, current_user_id)

        async with await self._get_user_lock(user_id):
            result = await self.db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()

            if not wallet:
                wallet = Wallet(user_id=user_id)
                self.db.add(wallet)
                await self.db.commit()
                await self.db.refresh(wallet)

            return wallet

    async def get_wallet_balance(self, user_id: int, current_user_id: int) -> Tuple[Decimal, Decimal]:
        """Get user's available and locked balance with ownership validation"""
        await self._validate_user_ownership(user_id, current_user_id)

        wallet = await self.get_or_create_wallet(user_id, current_user_id)
        return Decimal(str(wallet.balance)), Decimal(str(wallet.locked_balance))

    async def add_funds(self, user_id: int, amount: float, transaction_type: TransactionType,
                       description: Optional[str] = None, metadata: Optional[dict] = None,
                       current_user_id: int = None) -> Transaction:
        """Add funds to user wallet with comprehensive security checks"""
        if current_user_id is None:
            current_user_id = user_id

        await self._validate_user_ownership(user_id, current_user_id)
        amount_decimal = await self._validate_amount(amount)

        # Check daily limits
        await self._check_daily_limits(user_id, amount_decimal, transaction_type)

        async with await self._get_user_lock(user_id):
            wallet = await self.get_or_create_wallet(user_id, current_user_id)

            # Create transaction record first
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=transaction_type,
                amount=float(amount_decimal),
                status=TransactionStatus.PENDING,
                description=description,
                metadata=json.dumps(metadata) if metadata else None
            )

            self.db.add(transaction)
            await self.db.flush()

            # Atomic balance update
            success = await self._atomic_balance_update(
                wallet.id,
                amount_decimal,
                Decimal('0')
            )

            if not success:
                await self.db.rollback()
                raise InsufficientFundsError("Insufficient balance for transaction")

            # Update wallet totals
            if transaction_type == TransactionType.DEPOSIT:
                await self.db.execute(
                    update(Wallet)
                    .where(Wallet.id == wallet.id)
                    .values(total_deposited=Wallet.total_deposited + float(amount_decimal))
                )

            await self.db.commit()
            await self.db.refresh(transaction)

            logger.info(f"Funds added: User {user_id}, Amount: {amount_decimal}, Type: {transaction_type}")

            return transaction

    async def lock_funds(self, user_id: int, amount: float, description: str,
                        current_user_id: int = None) -> Transaction:
        """Lock funds for betting with atomic operations"""
        if current_user_id is None:
            current_user_id = user_id

        await self._validate_user_ownership(user_id, current_user_id)
        amount_decimal = await self._validate_amount(amount)

        async with await self._get_user_lock(user_id):
            wallet = await self.get_or_create_wallet(user_id, current_user_id)

            # Check sufficient balance
            if Decimal(str(wallet.balance)) < amount_decimal:
                raise InsufficientFundsError("Insufficient balance for this transaction")

            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=TransactionType.BET_PLACED,
                amount=float(amount_decimal),
                status=TransactionStatus.PENDING,
                description=description
            )

            self.db.add(transaction)
            await self.db.flush()

            # Atomic balance update: move from balance to locked
            success = await self._atomic_balance_update(
                wallet.id,
                -amount_decimal,  # Remove from balance
                amount_decimal     # Add to locked
            )

            if not success:
                await self.db.rollback()
                raise InsufficientFundsError("Failed to lock funds")

            # Update total wagered
            await self.db.execute(
                update(Wallet)
                .where(Wallet.id == wallet.id)
                .values(total_wagered=Wallet.total_wagered + float(amount_decimal))
            )

            await self.db.commit()
            await self.db.refresh(transaction)

            logger.info(f"Funds locked: User {user_id}, Amount: {amount_decimal}")

            return transaction

    async def unlock_funds(self, user_id: int, amount: float, description: str,
                          current_user_id: int = None) -> Transaction:
        """Unlock funds back to available balance"""
        if current_user_id is None:
            current_user_id = user_id

        await self._validate_user_ownership(user_id, current_user_id)
        amount_decimal = await self._validate_amount(amount)

        async with await self._get_user_lock(user_id):
            wallet = await self.get_or_create_wallet(user_id, current_user_id)

            if Decimal(str(wallet.locked_balance)) < amount_decimal:
                raise InsufficientFundsError("Insufficient locked balance")

            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=TransactionType.REFUND,
                amount=float(amount_decimal),
                status=TransactionStatus.PENDING,
                description=description
            )

            self.db.add(transaction)
            await self.db.flush()

            # Atomic balance update: move from locked back to balance
            success = await self._atomic_balance_update(
                wallet.id,
                amount_decimal,   # Add to balance
                -amount_decimal   # Remove from locked
            )

            if not success:
                await self.db.rollback()
                raise InsufficientFundsError("Failed to unlock funds")

            await self.db.commit()
            await self.db.refresh(transaction)

            logger.info(f"Funds unlocked: User {user_id}, Amount: {amount_decimal}")

            return transaction

    async def process_win(self, user_id: int, amount: float, description: str,
                         current_user_id: int = None) -> Transaction:
        """Process winning bet payout"""
        if current_user_id is None:
            current_user_id = user_id

        await self._validate_user_ownership(user_id, current_user_id)
        amount_decimal = await self._validate_amount(amount)

        async with await self._get_user_lock(user_id):
            wallet = await self.get_or_create_wallet(user_id, current_user_id)

            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=TransactionType.BET_WON,
                amount=float(amount_decimal),
                status=TransactionStatus.PENDING,
                description=description
            )

            self.db.add(transaction)
            await self.db.flush()

            # Atomic balance update: add winnings to balance
            success = await self._atomic_balance_update(wallet.id, amount_decimal)

            if not success:
                await self.db.rollback()
                raise SecurityError("Failed to process winnings")

            # Update total won
            await self.db.execute(
                update(Wallet)
                .where(Wallet.id == wallet.id)
                .values(total_won=Wallet.total_won + float(amount_decimal))
            )

            await self.db.commit()
            await self.db.refresh(transaction)

            logger.info(f"Win processed: User {user_id}, Amount: {amount_decimal}")

            return transaction

    async def process_loss(self, user_id: int, amount: float, description: str,
                          current_user_id: int = None) -> Transaction:
        """Process losing bet (funds already locked)"""
        if current_user_id is None:
            current_user_id = user_id

        await self._validate_user_ownership(user_id, current_user_id)
        amount_decimal = await self._validate_amount(amount)

        async with await self._get_user_lock(user_id):
            wallet = await self.get_or_create_wallet(user_id, current_user_id)

            if Decimal(str(wallet.locked_balance)) < amount_decimal:
                raise InsufficientFundsError("Insufficient locked balance")

            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=TransactionType.BET_LOST,
                amount=float(amount_decimal),
                status=TransactionStatus.PENDING,
                description=description
            )

            self.db.add(transaction)
            await self.db.flush()

            # Atomic balance update: remove from locked balance
            success = await self._atomic_balance_update(wallet.id, Decimal('0'), -amount_decimal)

            if not success:
                await self.db.rollback()
                raise SecurityError("Failed to process loss")

            await self.db.commit()
            await self.db.refresh(transaction)

            logger.info(f"Loss processed: User {user_id}, Amount: {amount_decimal}")

            return transaction

    async def get_transactions(self, user_id: int, current_user_id: int,
                              page: int = 1, limit: int = 20) -> Tuple[List[Transaction], int]:
        """Get user transactions with ownership validation"""
        await self._validate_user_ownership(user_id, current_user_id)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        )
        total = count_result.scalar()

        # Get transactions with pagination
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        transactions = result.scalars().all()

        return list(transactions), total
