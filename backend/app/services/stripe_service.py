"""
Stripe payment processing service
"""

import stripe
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import GambleGleeException

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Stripe payment processing service"""

    @staticmethod
    async def create_customer(user_id: int, email: str, name: Optional[str] = None) -> str:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    'user_id': str(user_id),
                    'platform': 'gambleglee'
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create Stripe customer: {str(e)}")

    @staticmethod
    async def create_payment_intent(
        amount: int,  # Amount in cents
        customer_id: str,
        currency: str = "usd",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment intent for deposits"""
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
                confirmation_method='manual',
                confirm=True
            )

            return {
                'id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'status': payment_intent.status
            }
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create payment intent: {str(e)}")

    @staticmethod
    async def create_setup_intent(customer_id: str) -> Dict[str, Any]:
        """Create a setup intent for saving payment methods"""
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card'],
                usage='off_session'
            )

            return {
                'id': setup_intent.id,
                'client_secret': setup_intent.client_secret,
                'status': setup_intent.status
            }
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create setup intent: {str(e)}")

    @staticmethod
    async def create_transfer(
        amount: int,  # Amount in cents
        destination_account: str,
        currency: str = "usd",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a transfer for withdrawals"""
        try:
            transfer = stripe.Transfer.create(
                amount=amount,
                currency=currency,
                destination=destination_account,
                metadata=metadata or {}
            )

            return {
                'id': transfer.id,
                'status': transfer.status,
                'amount': transfer.amount
            }
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create transfer: {str(e)}")

    @staticmethod
    async def get_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """Get payment intent details"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'customer': payment_intent.customer
            }
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to retrieve payment intent: {str(e)}")

    @staticmethod
    async def handle_webhook(payload: str, signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )

            return {
                'type': event['type'],
                'data': event['data']['object'],
                'id': event['id']
            }
        except stripe.error.SignatureVerificationError:
            raise GambleGleeException("Invalid webhook signature")
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Webhook processing failed: {str(e)}")

    @staticmethod
    async def create_connect_account(user_id: int, email: str) -> str:
        """Create a Stripe Connect account for peer-to-peer transfers"""
        try:
            account = stripe.Account.create(
                type='express',
                country='US',
                email=email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                metadata={
                    'user_id': str(user_id),
                    'platform': 'gambleglee'
                }
            )
            return account.id
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create Connect account: {str(e)}")

    @staticmethod
    async def create_account_link(account_id: str, refresh_url: str, return_url: str) -> str:
        """Create an account link for Connect onboarding"""
        try:
            account_link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            return account_link.url
        except stripe.error.StripeError as e:
            raise GambleGleeException(f"Failed to create account link: {str(e)}")
