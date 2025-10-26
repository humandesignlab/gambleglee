"""
Location detection endpoints
"""

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import (get_compliance_requirements,
                                   get_payment_methods, get_payment_processor,
                                   get_user_location)

router = APIRouter()


@router.get("/location")
async def get_location_info(
    location: dict = Depends(get_user_location),
    payment_processor: str = Depends(get_payment_processor),
    payment_methods: list = Depends(get_payment_methods),
    compliance_requirements: dict = Depends(get_compliance_requirements),
):
    """Get user location and compliance information"""
    return {
        "location": location,
        "payment_processor": payment_processor,
        "payment_methods": payment_methods,
        "compliance_requirements": compliance_requirements,
    }
