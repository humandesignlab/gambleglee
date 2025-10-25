"""
Wallet and transaction schemas
"""

from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class WalletResponse(BaseModel):
    """Wallet response schema"""
    id: int
    user_id: int
    balance: float
    locked_balance: float
    total_deposited: float
    total_withdrawn: float
    total_wagered: float
    total_won: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Transaction response schema"""
    id: int
    user_id: int
    wallet_id: int
    type: str
    amount: float
    status: str
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepositRequest(BaseModel):
    """Deposit request schema"""
    amount: float
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > 10000:  # Max deposit limit for MVP
            raise ValueError('Amount cannot exceed $10,000')
        return v


class WithdrawalRequest(BaseModel):
    """Withdrawal request schema"""
    amount: float
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > 5000:  # Max withdrawal limit for MVP
            raise ValueError('Amount cannot exceed $5,000')
        return v


class StripePaymentIntentResponse(BaseModel):
    """Stripe payment intent response"""
    client_secret: str
    payment_intent_id: str


class TransactionListResponse(BaseModel):
    """Transaction list response"""
    items: List[TransactionResponse]
    total: int
    page: int
    size: int
    pages: int
