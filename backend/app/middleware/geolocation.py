"""
Geolocation middleware for automatic location detection
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
import time
from typing import Dict, Any

from app.services.geolocation_service import GeolocationService


class GeolocationMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically detect user location"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.geolocation_service = GeolocationService()

    async def dispatch(self, request: Request, call_next):
        """Process request and add location data"""
        start_time = time.time()

        # Skip geolocation for certain paths
        if self._should_skip_geolocation(request):
            response = await call_next(request)
            return response

        try:
            # Get user location
            location_data = await self.geolocation_service.get_user_location(request)

            # Add location data to request state
            request.state.location = location_data
            request.state.payment_processor = self.geolocation_service.get_payment_processor(location_data)
            request.state.payment_methods = self.geolocation_service.get_payment_methods(location_data)
            request.state.compliance_requirements = self.geolocation_service.get_compliance_requirements(location_data)

            # Add location headers for debugging
            response = await call_next(request)
            response.headers["X-Detected-Country"] = location_data.get("country", "UNKNOWN")
            response.headers["X-Payment-Processor"] = request.state.payment_processor
            response.headers["X-Compliance-Status"] = location_data.get("compliance_status", "unknown")

        except Exception as e:
            # If geolocation fails, use default US location
            request.state.location = {
                "country": "US",
                "country_name": "United States",
                "compliance_status": "allowed",
                "compliance_reason": "Default location",
                "source": "fallback"
            }
            request.state.payment_processor = "stripe"
            request.state.payment_methods = ["card", "ach", "bank_transfer"]
            request.state.compliance_requirements = {
                "kyc_required": True,
                "age_verification": True,
                "currency": "USD"
            }

            response = await call_next(request)
            response.headers["X-Detected-Country"] = "US"
            response.headers["X-Payment-Processor"] = "stripe"
            response.headers["X-Compliance-Status"] = "fallback"

        # Add processing time header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _should_skip_geolocation(self, request: Request) -> bool:
        """Determine if geolocation should be skipped for this request"""
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]

        return any(request.url.path.startswith(path) for path in skip_paths)
