"""
MercadoPago payment processing service for Mexico
"""

import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import GambleGleeException


class MercadoPagoService:
    """MercadoPago payment processing service for Mexico"""

    def __init__(self):
        self.access_token = settings.MERCADOPAGO_ACCESS_TOKEN
        self.base_url = "https://api.mercadopago.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def create_customer(self, user_id: int, email: str, name: Optional[str] = None) -> str:
        """Create a MercadoPago customer"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/customers",
                    headers=self.headers,
                    json={
                        "email": email,
                        "first_name": name.split()[0] if name and name.split() else None,
                        "last_name": name.split()[-1] if name and len(name.split()) > 1 else None,
                        "metadata": {
                            "user_id": str(user_id),
                            "platform": "gambleglee"
                        }
                    }
                )

                if response.status_code == 201:
                    data = response.json()
                    return data["id"]
                else:
                    raise GambleGleeException(f"Failed to create MercadoPago customer: {response.text}")
        except httpx.RequestError as e:
            raise GambleGleeException(f"Failed to create MercadoPago customer: {str(e)}")

    async def create_payment_intent(
        self,
        amount: float,
        customer_id: str,
        currency: str = "MXN",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment intent for deposits"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/payments",
                    headers=self.headers,
                    json={
                        "transaction_amount": amount,
                        "currency_id": currency,
                        "customer_id": customer_id,
                        "description": "GambleGlee Deposit",
                        "payment_method_id": "pix",  # Default to PIX for Brazil, but we'll use card
                        "installments": 1,
                        "metadata": metadata or {}
                    }
                )

                if response.status_code == 201:
                    data = response.json()
                    return {
                        "id": data["id"],
                        "status": data["status"],
                        "transaction_amount": data["transaction_amount"],
                        "currency_id": data["currency_id"]
                    }
                else:
                    raise GambleGleeException(f"Failed to create payment: {response.text}")
        except httpx.RequestError as e:
            raise GambleGleeException(f"Failed to create payment: {str(e)}")

    async def create_preference(
        self,
        amount: float,
        customer_id: str,
        currency: str = "MXN",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment preference for OXXO and other payment methods"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/checkout/preferences",
                    headers=self.headers,
                    json={
                        "items": [
                            {
                                "title": "GambleGlee Deposit",
                                "quantity": 1,
                                "unit_price": amount,
                                "currency_id": currency
                            }
                        ],
                        "payer": {
                            "id": customer_id
                        },
                        "payment_methods": {
                            "excluded_payment_methods": [],
                            "excluded_payment_types": [],
                            "installments": 1
                        },
                        "back_urls": {
                            "success": f"{settings.FRONTEND_URL}/wallet?status=success",
                            "failure": f"{settings.FRONTEND_URL}/wallet?status=failure",
                            "pending": f"{settings.FRONTEND_URL}/wallet?status=pending"
                        },
                        "auto_return": "approved",
                        "metadata": metadata or {}
                    }
                )

                if response.status_code == 201:
                    data = response.json()
                    return {
                        "id": data["id"],
                        "init_point": data["init_point"],
                        "sandbox_init_point": data.get("sandbox_init_point"),
                        "status": "pending"
                    }
                else:
                    raise GambleGleeException(f"Failed to create preference: {response.text}")
        except httpx.RequestError as e:
            raise GambleGleeException(f"Failed to create preference: {str(e)}")

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment details"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/payments/{payment_id}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    raise GambleGleeException(f"Failed to get payment: {response.text}")
        except httpx.RequestError as e:
            raise GambleGleeException(f"Failed to get payment: {str(e)}")

    async def create_connect_account(self, user_id: int, email: str) -> str:
        """Create a MercadoPago Connect account for peer-to-peer transfers"""
        try:
            # For now, return a placeholder - MercadoPago Connect requires special approval
            return f"mp_connect_{user_id}"
        except Exception as e:
            raise GambleGleeException(f"Failed to create Connect account: {str(e)}")

    async def create_transfer(
        self,
        amount: float,
        destination_account: str,
        currency: str = "MXN",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a transfer for withdrawals"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/transfers",
                    headers=self.headers,
                    json={
                        "amount": amount,
                        "currency_id": currency,
                        "destination_user_id": destination_account,
                        "metadata": metadata or {}
                    }
                )

                if response.status_code == 201:
                    data = response.json()
                    return {
                        "id": data["id"],
                        "status": data["status"],
                        "amount": data["amount"]
                    }
                else:
                    raise GambleGleeException(f"Failed to create transfer: {response.text}")
        except httpx.RequestError as e:
            raise GambleGleeException(f"Failed to create transfer: {str(e)}")

    async def handle_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """Handle MercadoPago webhook events"""
        try:
            # MercadoPago webhook verification would go here
            # For now, return the payload
            return {
                "type": "payment",
                "data": payload,
                "id": "webhook_id"
            }
        except Exception as e:
            raise GambleGleeException(f"Webhook processing failed: {str(e)}")
