"""
FastAPI dependencies for common functionality
"""

from fastapi import Depends, Request
from typing import Dict, Any, Optional
from app.services.geolocation_service import GeolocationService


async def get_user_location(request: Request) -> Dict[str, Any]:
    """Get user location data from request state"""
    return getattr(request.state, 'location', {
        "country": "US",
        "country_name": "United States",
        "compliance_status": "allowed",
        "source": "default"
    })


async def get_payment_processor(request: Request) -> str:
    """Get payment processor for user's location"""
    return getattr(request.state, 'payment_processor', 'stripe')


async def get_payment_methods(request: Request) -> list:
    """Get available payment methods for user's location"""
    return getattr(request.state, 'payment_methods', ['card', 'ach', 'bank_transfer'])


async def get_compliance_requirements(request: Request) -> Dict[str, Any]:
    """Get compliance requirements for user's location"""
    return getattr(request.state, 'compliance_requirements', {
        "kyc_required": True,
        "age_verification": True,
        "currency": "USD"
    })


async def get_user_country(request: Request) -> str:
    """Get user's country code"""
    location = await get_user_location(request)
    return location.get("country", "US")


async def is_location_allowed(request: Request) -> bool:
    """Check if user's location is allowed"""
    location = await get_user_location(request)
    return location.get("compliance_status") == "allowed"
