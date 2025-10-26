"""
Social endpoints for GambleGlee
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (ActivityNotFoundError,
                                 FriendshipNotFoundError,
                                 NotificationNotFoundError, UserNotFoundError,
                                 ValidationError)
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.social import (ActivityCommentResponse, ActivityCreateRequest,
                                ActivityData, ActivityFilters,
                                ActivityListResponse, CommentCreateRequest,
                                FriendRequestRequest, FriendRequestResponse,
                                FriendshipListResponse, FriendshipResponse,
                                LeaderboardEntryResponse,
                                LeaderboardListResponse, LeaderboardRequest,
                                NotificationCreateRequest, NotificationFilters,
                                NotificationListResponse, NotificationResponse,
                                ProfileUpdateRequest, SocialDashboardResponse,
                                UserAchievementResponse, UserActivityResponse,
                                UserProfileResponse, UserSearchFilters,
                                UserSearchListResponse, UserSearchRequest,
                                UserSearchResponse, UserStatsResponse)
from app.services.social_service import SocialService

logger = structlog.get_logger(__name__)
router = APIRouter()

# === FRIEND SYSTEM ENDPOINTS ===


@router.post(
    "/friends/request",
    response_model=FriendshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_friend_request(
    friend_request: FriendRequestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a friend request to another user"""
    try:
        social_service = SocialService(db)
        friendship = await social_service.send_friend_request(
            current_user.id, friend_request.friend_id, friend_request.message
        )
        return FriendshipResponse.from_orm(friendship)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to send friend request", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send friend request",
        )


@router.post("/friends/respond", response_model=FriendshipResponse)
async def respond_to_friend_request(
    friend_response: FriendRequestResponse,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Respond to a friend request"""
    try:
        social_service = SocialService(db)
        friendship = await social_service.respond_to_friend_request(
            current_user.id, friend_response.friend_id, friend_response.action
        )
        return FriendshipResponse.from_orm(friendship)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FriendshipNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to respond to friend request", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to friend request",
        )


@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a friend"""
    try:
        social_service = SocialService(db)
        await social_service.remove_friend(current_user.id, friend_id)
        return {"message": "Friend removed successfully"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to remove friend", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove friend",
        )


@router.post("/friends/{friend_id}/block", response_model=FriendshipResponse)
async def block_user(
    friend_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Block a user"""
    try:
        social_service = SocialService(db)
        friendship = await social_service.block_user(current_user.id, friend_id)
        return FriendshipResponse.from_orm(friendship)
    except Exception as e:
        logger.error("Failed to block user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to block user",
        )


@router.get("/friends", response_model=FriendshipListResponse)
async def get_friends(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get user's friends list"""
    try:
        social_service = SocialService(db)
        friendships, total = await social_service.get_friends(
            current_user.id, page, size
        )

        return FriendshipListResponse(
            items=[FriendshipResponse.from_orm(f) for f in friendships],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )
    except Exception as e:
        logger.error("Failed to get friends", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get friends",
        )


@router.get("/friends/requests", response_model=FriendshipListResponse)
async def get_friend_requests(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get pending friend requests"""
    try:
        social_service = SocialService(db)
        friendships, total = await social_service.get_friend_requests(
            current_user.id, page, size
        )

        return FriendshipListResponse(
            items=[FriendshipResponse.from_orm(f) for f in friendships],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )
    except Exception as e:
        logger.error("Failed to get friend requests", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get friend requests",
        )


# === USER SEARCH ENDPOINTS ===


@router.post("/search/users", response_model=UserSearchListResponse)
async def search_users(
    search_request: UserSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for users"""
    try:
        social_service = SocialService(db)

        # Convert filters if provided
        filters = None
        if search_request.filters:
            filters = UserSearchFilters(**search_request.filters)

        users, total = await social_service.search_users(
            search_request.query,
            current_user.id,
            filters,
            search_request.page,
            search_request.size,
        )

        # Convert to response format
        user_responses = []
        for user in users:
            # Check friendship status
            friendship_status = None
            # This would be implemented to check friendship status

            user_responses.append(
                UserSearchResponse(
                    id=user.id,
                    username=user.username,
                    display_name=user.display_name or user.username,
                    avatar_url=user.avatar_url,
                    bio=user.bio,
                    location=user.location,
                    is_online=user.last_active
                    and (user.last_active > datetime.utcnow() - timedelta(minutes=5)),
                    last_active=user.last_active,
                    friends_count=0,  # This would be fetched from profile
                    total_bets=0,  # This would be fetched from profile
                    win_rate=0.0,  # This would be fetched from profile
                    is_friend=False,  # This would be determined by friendship status
                    friendship_status=friendship_status,
                )
            )

        return UserSearchListResponse(
            items=user_responses,
            total=total,
            page=search_request.page,
            size=search_request.size,
            pages=(total + search_request.size - 1) // search_request.size,
        )
    except Exception as e:
        logger.error("Failed to search users", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users",
        )


# === ACTIVITY FEED ENDPOINTS ===


@router.post(
    "/activities",
    response_model=UserActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_activity(
    activity_request: ActivityCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new activity"""
    try:
        social_service = SocialService(db)
        activity = await social_service.create_activity(
            ActivityData(
                user_id=current_user.id,
                activity_type=activity_request.activity_type,
                title=activity_request.title,
                description=activity_request.description,
                metadata=activity_request.metadata,
                is_public=activity_request.is_public,
            )
        )
        return UserActivityResponse.from_orm(activity)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to create activity", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create activity",
        )


@router.get("/activities", response_model=ActivityListResponse)
async def get_user_activities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    is_featured: Optional[bool] = Query(None),
):
    """Get user's activities"""
    try:
        social_service = SocialService(db)

        # Create filters
        filters = ActivityFilters(
            activity_type=activity_type, is_public=is_public, is_featured=is_featured
        )

        activities, total = await social_service.get_user_activities(
            current_user.id, page, size, filters
        )

        return ActivityListResponse(
            items=[UserActivityResponse.from_orm(a) for a in activities],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )
    except Exception as e:
        logger.error("Failed to get user activities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user activities",
        )


@router.get("/activities/friends", response_model=ActivityListResponse)
async def get_friends_activities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get friends' activities"""
    try:
        social_service = SocialService(db)
        activities, total = await social_service.get_friends_activities(
            current_user.id, page, size
        )

        return ActivityListResponse(
            items=[UserActivityResponse.from_orm(a) for a in activities],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )
    except Exception as e:
        logger.error("Failed to get friends activities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get friends activities",
        )


# === NOTIFICATION ENDPOINTS ===


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    notification_type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    is_important: Optional[bool] = Query(None),
):
    """Get user's notifications"""
    try:
        social_service = SocialService(db)

        # Create filters
        filters = NotificationFilters(
            notification_type=notification_type,
            is_read=is_read,
            is_important=is_important,
        )

        (
            notifications,
            total,
            unread_count,
        ) = await social_service.get_user_notifications(
            current_user.id, page, size, filters
        )

        return NotificationListResponse(
            items=[NotificationResponse.from_orm(n) for n in notifications],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
            unread_count=unread_count,
        )
    except Exception as e:
        logger.error("Failed to get notifications", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notifications",
        )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    try:
        social_service = SocialService(db)
        await social_service.mark_notification_read(notification_id, current_user.id)
        return {"message": "Notification marked as read"}
    except NotificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to mark notification as read", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read",
        )


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read"""
    try:
        social_service = SocialService(db)
        count = await social_service.mark_all_notifications_read(current_user.id)
        return {"message": f"Marked {count} notifications as read"}
    except Exception as e:
        logger.error("Failed to mark all notifications as read", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read",
        )


# === LEADERBOARD ENDPOINTS ===


@router.get("/leaderboards/{category}", response_model=LeaderboardListResponse)
async def get_leaderboard(
    category: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    time_period: str = Query("all_time"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get leaderboard entries"""
    try:
        social_service = SocialService(db)
        entries, total = await social_service.get_leaderboard(
            category, time_period, page, size
        )

        return LeaderboardListResponse(
            items=[LeaderboardEntryResponse.from_orm(e) for e in entries],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size,
        )
    except Exception as e:
        logger.error("Failed to get leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get leaderboard",
        )


# === DASHBOARD ENDPOINT ===


@router.get("/dashboard", response_model=SocialDashboardResponse)
async def get_social_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get social dashboard data"""
    try:
        social_service = SocialService(db)

        # This would be implemented to get comprehensive dashboard data
        # For now, return a basic response structure

        return SocialDashboardResponse(
            user_profile=None,  # This would be fetched
            recent_activities=[],  # This would be fetched
            friends_activities=[],  # This would be fetched
            notifications=[],  # This would be fetched
            achievements=[],  # This would be fetched
            leaderboard_position=None,  # This would be fetched
            stats=None,  # This would be fetched
        )
    except Exception as e:
        logger.error("Failed to get social dashboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get social dashboard",
        )
