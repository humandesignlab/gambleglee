"""
API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, wallet, bets, friends, events, stream

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(bets.router, prefix="/bets", tags=["bets"])
api_router.include_router(friends.router, prefix="/friends", tags=["friends"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
