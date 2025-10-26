"""
Wallet service for managing user finances
"""

from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.services.stripe_service import StripeService
from app.services.mercadopago_service import MercadoPagoService
from app.core.exceptions import InsufficientFundsError, ValidationError


class WalletService:
    """Wallet service for managing user finances"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stripe_service = StripeService()
        self.mercadopago_service = MercadoPagoService()

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        """Get or create user wallet"""
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()

        if not wallet:
            wallet = Wallet(user_id=user_id)
            self.db.add(wallet)
            await self.db.commit()
            await self.db.refresh(wallet)

        return wallet

    async def get_wallet_balance(self, user_id: int) -> Tuple[float, float]:
        """Get user's available and locked balance"""
        wallet = await self.get_or_create_wallet(user_id)
        return float(wallet.balance), float(wallet.locked_balance)

    async def add_funds(
        self,
        user_id: int,
        amount: float,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Transaction:
        """Add funds to user wallet"""
        wallet = await self.get_or_create_wallet(user_id)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=transaction_type,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=str(metadata) if metadata else None,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Update wallet balance
        wallet.balance += amount
        if transaction_type == TransactionType.DEPOSIT:
            wallet.total_deposited += amount

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def lock_funds(
        self, user_id: int, amount: float, description: str
    ) -> Transaction:
        """Lock funds for betting (escrow)"""
        wallet = await self.get_or_create_wallet(user_id)

        if wallet.balance < amount:
            raise InsufficientFundsError("Insufficient balance for this transaction")

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.BET_PLACED,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Move funds from balance to locked
        wallet.balance -= amount
        wallet.locked_balance += amount
        wallet.total_wagered += amount

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def unlock_funds(
        self, user_id: int, amount: float, description: str
    ) -> Transaction:
        """Unlock funds back to available balance"""
        wallet = await self.get_or_create_wallet(user_id)

        if wallet.locked_balance < amount:
            raise InsufficientFundsError("Insufficient locked balance")

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.REFUND,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Move funds from locked back to balance
        wallet.locked_balance -= amount
        wallet.balance += amount

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def process_win(
        self, user_id: int, amount: float, description: str
    ) -> Transaction:
        """Process winning bet payout"""
        wallet = await self.get_or_create_wallet(user_id)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.BET_WON,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Add winnings to balance
        wallet.balance += amount
        wallet.total_won += amount

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def process_loss(
        self, user_id: int, amount: float, description: str
    ) -> Transaction:
        """Process losing bet (funds already locked)"""
        wallet = await self.get_or_create_wallet(user_id)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.BET_LOST,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=description,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Remove funds from locked balance (already deducted from available)
        wallet.locked_balance -= amount

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def create_deposit_intent(
        self, user_id: int, amount: float, payment_processor: str = "stripe"
    ) -> dict:
        """Create payment intent for deposit"""
        # Get user for payment processor customer
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()

        if payment_processor == "stripe":
            # Create or get Stripe customer
            if not user.stripe_customer_id:
                customer_id = await self.stripe_service.create_customer(
                    user_id=user_id,
                    email=user.email,
                    name=(
                        f"{user.first_name} {user.last_name}".strip()
                        if user.first_name
                        else None
                    ),
                )
                user.stripe_customer_id = customer_id
                await self.db.commit()
            else:
                customer_id = user.stripe_customer_id

            # Create Stripe payment intent
            amount_cents = int(amount * 100)  # Convert to cents
            payment_intent = await self.stripe_service.create_payment_intent(
                amount=amount_cents,
                customer_id=customer_id,
                metadata={
                    "user_id": str(user_id),
                    "type": "deposit",
                    "amount": str(amount),
                },
            )

            return {
                "client_secret": payment_intent["client_secret"],
                "payment_intent_id": payment_intent["id"],
            }

        elif payment_processor == "mercadopago":
            # Create or get MercadoPago customer
            if not user.mercadopago_customer_id:
                customer_id = await self.mercadopago_service.create_customer(
                    user_id=user_id,
                    email=user.email,
                    name=(
                        f"{user.first_name} {user.last_name}".strip()
                        if user.first_name
                        else None
                    ),
                )
                user.mercadopago_customer_id = customer_id
                await self.db.commit()
            else:
                customer_id = user.mercadopago_customer_id

            # Create MercadoPago preference
            preference = await self.mercadopago_service.create_preference(
                amount=amount,
                customer_id=customer_id,
                currency="MXN",
                metadata={
                    "user_id": str(user_id),
                    "type": "deposit",
                    "amount": str(amount),
                },
            )

            return {
                "preference_id": preference["id"],
                "init_point": preference["init_point"],
                "sandbox_init_point": preference.get("sandbox_init_point"),
            }

        else:
            raise ValidationError(f"Unsupported payment processor: {payment_processor}")

    async def confirm_deposit(self, payment_intent_id: str) -> Transaction:
        """Confirm deposit after successful payment"""
        # Get payment intent from Stripe
        payment_intent = await self.stripe_service.get_payment_intent(payment_intent_id)

        if payment_intent["status"] != "succeeded":
            raise ValidationError("Payment not completed")

        # Extract user_id from metadata
        user_id = int(payment_intent.get("metadata", {}).get("user_id", 0))
        if not user_id:
            raise ValidationError("Invalid payment intent")

        amount = payment_intent["amount"] / 100  # Convert from cents

        # Create deposit transaction
        transaction = await self.add_funds(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            description=f"Deposit via Stripe - {payment_intent_id}",
            metadata={"stripe_payment_intent_id": payment_intent_id},
        )

        # Mark transaction as completed
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = func.now()
        await self.db.commit()

        return transaction

    async def request_withdrawal(self, user_id: int, amount: float) -> Transaction:
        """Request withdrawal (will be processed manually for MVP)"""
        wallet = await self.get_or_create_wallet(user_id)

        if wallet.balance < amount:
            raise InsufficientFundsError("Insufficient balance for withdrawal")

        # Create withdrawal transaction
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.WITHDRAWAL,
            amount=amount,
            status=TransactionStatus.PENDING,
            description="Withdrawal request",
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def get_transactions(
        self, user_id: int, page: int = 1, limit: int = 20
    ) -> Tuple[List[Transaction], int]:
        """Get user transactions with pagination"""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        )
        total = count_result.scalar()

        # Get transactions
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
