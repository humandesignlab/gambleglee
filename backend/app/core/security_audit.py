"""
Security audit and monitoring for wallet operations
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.wallet import Transaction, TransactionType, TransactionStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class SecurityAudit:
    """Security audit and monitoring for wallet operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_suspicious_activity(self, user_id: int) -> List[Dict[str, Any]]:
        """Detect suspicious wallet activity patterns"""
        alerts = []

        # Check for rapid transactions
        rapid_transactions = await self._check_rapid_transactions(user_id)
        if rapid_transactions:
            alerts.append({
                "type": "rapid_transactions",
                "severity": "high",
                "message": f"User {user_id} has {rapid_transactions} transactions in the last 5 minutes",
                "timestamp": datetime.utcnow()
            })

        # Check for unusual amounts
        unusual_amounts = await self._check_unusual_amounts(user_id)
        if unusual_amounts:
            alerts.append({
                "type": "unusual_amounts",
                "severity": "medium",
                "message": f"User {user_id} has transactions with unusual amounts",
                "timestamp": datetime.utcnow()
            })

        # Check for potential money laundering patterns
        ml_patterns = await self._check_money_laundering_patterns(user_id)
        if ml_patterns:
            alerts.append({
                "type": "money_laundering",
                "severity": "critical",
                "message": f"User {user_id} shows potential money laundering patterns",
                "timestamp": datetime.utcnow()
            })

        return alerts

    async def _check_rapid_transactions(self, user_id: int) -> int:
        """Check for rapid transaction patterns"""
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

        result = await self.db.execute(
            select(func.count(Transaction.id))
            .where(Transaction.user_id == user_id)
            .where(Transaction.created_at >= five_minutes_ago)
        )

        count = result.scalar()
        return count if count > 10 else 0  # Alert if more than 10 transactions in 5 minutes

    async def _check_unusual_amounts(self, user_id: int) -> bool:
        """Check for unusual transaction amounts"""
        # Get user's transaction history
        result = await self.db.execute(
            select(Transaction.amount)
            .where(Transaction.user_id == user_id)
            .where(Transaction.status == TransactionStatus.COMPLETED)
            .order_by(Transaction.created_at.desc())
            .limit(100)
        )

        amounts = [Decimal(str(amount)) for amount in result.scalars()]

        if len(amounts) < 5:
            return False

        # Calculate average and standard deviation
        avg_amount = sum(amounts) / len(amounts)
        variance = sum((amount - avg_amount) ** 2 for amount in amounts) / len(amounts)
        std_dev = variance ** 0.5

        # Check for amounts that are 3 standard deviations from the mean
        threshold = avg_amount + (3 * std_dev)
        unusual_count = sum(1 for amount in amounts if amount > threshold)

        return unusual_count > 2  # Alert if more than 2 unusual amounts

    async def _check_money_laundering_patterns(self, user_id: int) -> bool:
        """Check for potential money laundering patterns"""
        # Pattern 1: Rapid deposits followed by withdrawals
        recent_deposits = await self.db.execute(
            select(func.count(Transaction.id))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == TransactionType.DEPOSIT)
            .where(Transaction.created_at >= datetime.utcnow() - timedelta(hours=1))
        )

        recent_withdrawals = await self.db.execute(
            select(func.count(Transaction.id))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == TransactionType.WITHDRAWAL)
            .where(Transaction.created_at >= datetime.utcnow() - timedelta(hours=1))
        )

        deposit_count = recent_deposits.scalar()
        withdrawal_count = recent_withdrawals.scalar()

        # Alert if multiple deposits followed by withdrawals in short time
        if deposit_count > 3 and withdrawal_count > 2:
            return True

        # Pattern 2: Round number transactions (potential structuring)
        round_amounts = await self.db.execute(
            select(func.count(Transaction.id))
            .where(Transaction.user_id == user_id)
            .where(Transaction.amount.in_([100, 200, 500, 1000, 2000, 5000]))
            .where(Transaction.created_at >= datetime.utcnow() - timedelta(hours=24))
        )

        if round_amounts.scalar() > 5:
            return True

        return False

    async def audit_wallet_integrity(self, user_id: int) -> Dict[str, Any]:
        """Audit wallet balance integrity"""
        # Get all transactions for the user
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .where(Transaction.status == TransactionStatus.COMPLETED)
            .order_by(Transaction.created_at)
        )

        transactions = result.scalars().all()

        # Calculate expected balance
        expected_balance = Decimal('0')
        expected_locked = Decimal('0')

        for transaction in transactions:
            amount = Decimal(str(transaction.amount))

            if transaction.type == TransactionType.DEPOSIT:
                expected_balance += amount
            elif transaction.type == TransactionType.WITHDRAWAL:
                expected_balance -= amount
            elif transaction.type == TransactionType.BET_PLACED:
                expected_balance -= amount
                expected_locked += amount
            elif transaction.type == TransactionType.BET_WON:
                expected_balance += amount
            elif transaction.type == TransactionType.BET_LOST:
                expected_locked -= amount
            elif transaction.type == TransactionType.REFUND:
                expected_balance += amount
                expected_locked -= amount

        return {
            "user_id": user_id,
            "expected_balance": float(expected_balance),
            "expected_locked": float(expected_locked),
            "transaction_count": len(transactions),
            "audit_timestamp": datetime.utcnow()
        }

    async def log_security_event(self, event_type: str, user_id: int,
                                details: Dict[str, Any], severity: str = "medium"):
        """Log security events for monitoring"""
        logger.warning(f"SECURITY_EVENT: {event_type} | User: {user_id} | Severity: {severity} | Details: {details}")

        # In production, this would send to a security monitoring system
        # like Splunk, ELK stack, or AWS CloudWatch

    async def check_velocity_limits(self, user_id: int, amount: Decimal,
                                  transaction_type: TransactionType) -> bool:
        """Check velocity limits for transactions"""
        # Check hourly limits
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        result = await self.db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == transaction_type)
            .where(Transaction.created_at >= one_hour_ago)
            .where(Transaction.status == TransactionStatus.COMPLETED)
        )

        hourly_total = result.scalar() or 0

        # Set velocity limits based on transaction type
        if transaction_type == TransactionType.DEPOSIT:
            hourly_limit = 5000  # $5000 per hour
        elif transaction_type == TransactionType.WITHDRAWAL:
            hourly_limit = 10000  # $10000 per hour
        else:
            hourly_limit = 20000  # Default limit

        return (hourly_total + float(amount)) <= hourly_limit
