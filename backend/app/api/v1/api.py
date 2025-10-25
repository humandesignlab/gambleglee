"""
API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, wallet, bets, friends, events, stream, location, rewards, social

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(bets.router, prefix="/bets", tags=["bets"])
api_router.include_router(friends.router, prefix="/friends", tags=["friends"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(location.router, prefix="", tags=["location"])
api_router.include_router(rewards.router, prefix="/rewards", tags=["rewards"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
