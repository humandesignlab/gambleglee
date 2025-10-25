"""
Geolocation service for detecting user location and compliance
"""

import httpx
from typing import Optional, Dict, Any, Tuple
from fastapi import Request
from app.core.config import settings
from app.core.exceptions import ComplianceError


class GeolocationService:
    """Service for detecting user location and compliance requirements"""

    def __init__(self):
        self.allowed_countries = settings.ALLOWED_COUNTRIES
        self.allowed_states = settings.ALLOWED_STATES

    async def get_user_location(self, request: Request) -> Dict[str, Any]:
        """Get user location from IP address and headers"""
        # Get IP address
        ip_address = self._get_client_ip(request)

        # Get location from IP
        location_data = await self._get_location_from_ip(ip_address)

        # Get additional location hints from headers
        location_hints = self._get_location_hints(request)

        # Combine and validate location data
        return self._combine_location_data(location_data, location_hints, ip_address)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (common with proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        return request.client.host if request.client else "127.0.0.1"

    async def _get_location_from_ip(self, ip_address: str) -> Dict[str, Any]:
        """Get location data from IP address using geolocation service"""
        try:
            # Use ipapi.co (free tier: 1000 requests/day)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://ipapi.co/{ip_address}/json/",
                    timeout=5.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "country": data.get("country_code", "").upper(),
                        "country_name": data.get("country_name", ""),
                        "region": data.get("region", ""),
                        "city": data.get("city", ""),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timezone": data.get("timezone", ""),
                        "isp": data.get("org", ""),
                        "source": "ipapi"
                    }
        except Exception as e:
            print(f"IP geolocation failed: {e}")

        # Fallback to default location
        return {
            "country": "US",
            "country_name": "United States",
            "region": "",
            "city": "",
            "latitude": None,
            "longitude": None,
            "timezone": "UTC",
            "isp": "",
            "source": "fallback"
        }

    def _get_location_hints(self, request: Request) -> Dict[str, Any]:
        """Extract location hints from request headers"""
        hints = {}

        # Accept-Language header (gives country hints)
        accept_language = request.headers.get("Accept-Language", "")
        if "es-MX" in accept_language or "es-MX" in accept_language:
            hints["language_hint"] = "MX"
        elif "es" in accept_language:
            hints["language_hint"] = "ES"
        else:
            hints["language_hint"] = "EN"

        # Timezone header (if available)
        timezone = request.headers.get("X-Timezone")
        if timezone:
            hints["timezone"] = timezone

        # User-Agent analysis (basic)
        user_agent = request.headers.get("User-Agent", "")
        if "Windows" in user_agent:
            hints["os"] = "Windows"
        elif "Mac" in user_agent:
            hints["os"] = "macOS"
        elif "Linux" in user_agent:
            hints["os"] = "Linux"

        return hints

    def _combine_location_data(self, location_data: Dict[str, Any],
                             location_hints: Dict[str, Any],
                             ip_address: str) -> Dict[str, Any]:
        """Combine and validate location data"""
        combined = {
            **location_data,
            **location_hints,
            "ip_address": ip_address,
            "detected_at": "now()"  # Will be replaced with actual timestamp
        }

        # Validate country is allowed
        country = combined.get("country", "").upper()
        if country not in self.allowed_countries:
            combined["compliance_status"] = "blocked"
            combined["compliance_reason"] = f"Country {country} not allowed"
        else:
            combined["compliance_status"] = "allowed"
            combined["compliance_reason"] = "Location verified"

        # Check state restrictions (for US)
        if country == "US" and self.allowed_states:
            region = combined.get("region", "").upper()
            if region not in self.allowed_states:
                combined["compliance_status"] = "restricted"
                combined["compliance_reason"] = f"State {region} not allowed"

        return combined

    def get_payment_processor(self, location_data: Dict[str, Any]) -> str:
        """Determine which payment processor to use based on location"""
        country = location_data.get("country", "").upper()

        if country == "US":
            return "stripe"
        elif country == "MX":
            return "mercadopago"
        else:
            # For now, only support US and Mexico
            return "stripe"  # Default to Stripe for unsupported countries

    def get_payment_methods(self, location_data: Dict[str, Any]) -> list:
        """Get available payment methods for the user's location"""
        country = location_data.get("country", "").upper()

        if country == "US":
            return ["card", "ach", "bank_transfer"]
        elif country == "MX":
            return ["card", "oxxo", "bank_transfer", "mercadopago"]
        else:
            # For unsupported countries, show limited options
            return ["card", "bank_transfer"]

    def get_compliance_requirements(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get compliance requirements for the user's location"""
        country = location_data.get("country", "").upper()

        # Default requirements
        requirements = {
            "kyc_required": True,
            "age_verification": True,
            "tax_collection": True,
            "deposit_limits": {"daily": 1000, "weekly": 5000, "monthly": 20000},
            "withdrawal_limits": {"daily": 5000, "weekly": 10000, "monthly": 50000},
            "currency": "USD"
        }

        if country == "US":
            requirements.update({
                "kyc_required": True,
                "age_verification": True,
                "tax_collection": True,
                "deposit_limits": {"daily": 1000, "weekly": 5000, "monthly": 20000},
                "withdrawal_limits": {"daily": 5000, "weekly": 10000, "monthly": 50000},
                "currency": "USD"
            })
        elif country == "MX":
            requirements.update({
                "kyc_required": True,
                "age_verification": True,
                "tax_collection": True,
                "deposit_limits": {"daily": 500, "weekly": 2500, "monthly": 10000},
                "withdrawal_limits": {"daily": 2500, "weekly": 5000, "monthly": 25000},
                "currency": "MXN"
            })

        return requirements

    async def verify_location_compliance(self, location_data: Dict[str, Any]) -> bool:
        """Verify if user location is compliant with platform requirements"""
        compliance_status = location_data.get("compliance_status")

        if compliance_status == "blocked":
            raise ComplianceError("Access not allowed from this location")
        elif compliance_status == "restricted":
            raise ComplianceError("Limited access from this location")

        return True
