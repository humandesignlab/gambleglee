"""
Social service for GambleGlee
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import and_, asc, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import (
    ActivityNotFoundError,
    FriendshipNotFoundError,
    NotificationNotFoundError,
    UserNotFoundError,
    ValidationError,
)
from app.models.auth import User
from app.models.social import (
    ActivityComment,
    ActivityLike,
    ActivityType,
    Friendship,
    FriendshipStatus,
    Leaderboard,
    LeaderboardEntry,
    Notification,
    NotificationType,
    PrivacyLevel,
    UserAchievement,
    UserActivity,
    UserProfile,
    UserSearch,
)
from app.schemas.social import (
    AchievementData,
    ActivityData,
    ActivityFilters,
    FriendRequestRequest,
    LeaderboardData,
    LeaderboardEntryData,
    NotificationData,
    NotificationFilters,
    UserSearchFilters,
)

logger = structlog.get_logger(__name__)


class SocialService:
    """Comprehensive social service for user interactions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === FRIEND SYSTEM ===

    async def send_friend_request(
        self, user_id: int, friend_id: int, message: Optional[str] = None
    ) -> Friendship:
        """Send a friend request to another user"""

        # Check if users exist
        if user_id == friend_id:
            raise ValidationError("Cannot send friend request to yourself")

        # Check if friendship already exists
        existing_friendship = await self._get_friendship(user_id, friend_id)
        if existing_friendship:
            if existing_friendship.status == FriendshipStatus.ACCEPTED:
                raise ValidationError("Users are already friends")
            elif existing_friendship.status == FriendshipStatus.PENDING:
                raise ValidationError("Friend request already sent")
            elif existing_friendship.status == FriendshipStatus.BLOCKED:
                raise ValidationError("Cannot send friend request to blocked user")

        # Create friendship
        friendship = Friendship(
            user_id=user_id,
            friend_id=friend_id,
            status=FriendshipStatus.PENDING,
            initiated_by=user_id,
            notes=message,
        )

        self.db.add(friendship)
        await self.db.commit()
        await self.db.refresh(friendship)

        # Create notification for friend
        await self._create_notification(
            user_id=friend_id,
            notification_type=NotificationType.FRIEND_REQUEST,
            title="New Friend Request",
            message=f"You have a new friend request from {user_id}",
            metadata={"friendship_id": friendship.id, "requester_id": user_id},
        )

        logger.info("Friend request sent", user_id=user_id, friend_id=friend_id)
        return friendship

    async def respond_to_friend_request(
        self, user_id: int, friend_id: int, action: str
    ) -> Friendship:
        """Respond to a friend request"""

        friendship = await self._get_friendship(
            friend_id, user_id
        )  # Note: reversed order
        if not friendship:
            raise FriendshipNotFoundError("Friend request not found")

        if friendship.status != FriendshipStatus.PENDING:
            raise ValidationError("Friend request has already been responded to")

        if action == "accept":
            friendship.status = FriendshipStatus.ACCEPTED
            friendship.accepted_at = datetime.utcnow()

            # Update friend counts
            await self._update_friend_counts(user_id, friend_id, increment=True)

            # Create notifications
            await self._create_notification(
                user_id=friend_id,
                notification_type=NotificationType.FRIEND_ACCEPTED,
                title="Friend Request Accepted",
                message=f"Your friend request to {user_id} has been accepted",
                metadata={"friendship_id": friendship.id, "accepter_id": user_id},
            )

        elif action == "decline":
            friendship.status = FriendshipStatus.DECLINED

        elif action == "block":
            friendship.status = FriendshipStatus.BLOCKED

        else:
            raise ValidationError(
                "Invalid action. Must be 'accept', 'decline', or 'block'"
            )

        friendship.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(friendship)

        logger.info(
            "Friend request responded",
            user_id=user_id,
            friend_id=friend_id,
            action=action,
        )
        return friendship

    async def remove_friend(self, user_id: int, friend_id: int) -> bool:
        """Remove a friend"""

        friendship = await self._get_friendship(user_id, friend_id)
        if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
            raise ValidationError("Users are not friends")

        # Update friend counts
        await self._update_friend_counts(user_id, friend_id, increment=False)

        # Delete friendship
        await self.db.delete(friendship)
        await self.db.commit()

        logger.info("Friend removed", user_id=user_id, friend_id=friend_id)
        return True

    async def block_user(self, user_id: int, friend_id: int) -> Friendship:
        """Block a user"""

        # Check if friendship exists
        friendship = await self._get_friendship(user_id, friend_id)
        if not friendship:
            # Create new friendship with blocked status
            friendship = Friendship(
                user_id=user_id,
                friend_id=friend_id,
                status=FriendshipStatus.BLOCKED,
                initiated_by=user_id,
            )
            self.db.add(friendship)
        else:
            friendship.status = FriendshipStatus.BLOCKED
            friendship.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(friendship)

        logger.info("User blocked", user_id=user_id, friend_id=friend_id)
        return friendship

    async def get_friends(
        self, user_id: int, page: int = 1, size: int = 20
    ) -> Tuple[List[Friendship], int]:
        """Get user's friends list"""

        query = select(Friendship).where(
            and_(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == FriendshipStatus.ACCEPTED,
            )
        )

        # Count total
        total_query = select(func.count(Friendship.id)).where(
            and_(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == FriendshipStatus.ACCEPTED,
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * size).limit(size)
        query = query.options(
            selectinload(Friendship.user), selectinload(Friendship.friend)
        )

        result = await self.db.execute(query)
        friendships = result.scalars().all()

        return friendships, total

    async def get_friend_requests(
        self, user_id: int, page: int = 1, size: int = 20
    ) -> Tuple[List[Friendship], int]:
        """Get pending friend requests for user"""

        query = select(Friendship).where(
            and_(
                Friendship.friend_id == user_id,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )

        # Count total
        total_query = select(func.count(Friendship.id)).where(
            and_(
                Friendship.friend_id == user_id,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * size).limit(size)
        query = query.options(selectinload(Friendship.user))

        result = await self.db.execute(query)
        friendships = result.scalars().all()

        return friendships, total

    # === USER SEARCH ===

    async def search_users(
        self,
        query: str,
        user_id: Optional[int] = None,
        filters: Optional[UserSearchFilters] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[User], int]:
        """Search for users"""

        # Base query
        search_query = select(User).join(UserProfile, User.id == UserProfile.user_id)

        # Search conditions
        search_conditions = [
            or_(
                User.username.ilike(f"%{query}%"),
                User.display_name.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%"),
            )
        ]

        # Apply filters
        if filters:
            if filters.location:
                search_conditions.append(
                    UserProfile.location.ilike(f"%{filters.location}%")
                )
            if filters.min_friends is not None:
                search_conditions.append(
                    UserProfile.friends_count >= filters.min_friends
                )
            if filters.max_friends is not None:
                search_conditions.append(
                    UserProfile.friends_count <= filters.max_friends
                )
            if filters.min_win_rate is not None:
                search_conditions.append(UserProfile.win_rate >= filters.min_win_rate)
            if filters.max_win_rate is not None:
                search_conditions.append(UserProfile.win_rate <= filters.max_win_rate)
            if filters.is_online is not None:
                if filters.is_online:
                    search_conditions.append(
                        UserProfile.last_active
                        > datetime.utcnow() - timedelta(minutes=5)
                    )
                else:
                    search_conditions.append(
                        UserProfile.last_active
                        <= datetime.utcnow() - timedelta(minutes=5)
                    )
            if filters.has_avatar is not None:
                if filters.has_avatar:
                    search_conditions.append(User.avatar_url.isnot(None))
                else:
                    search_conditions.append(User.avatar_url.is_(None))

        # Apply search conditions
        search_query = search_query.where(and_(*search_conditions))

        # Count total
        total_query = (
            select(func.count(User.id))
            .join(UserProfile, User.id == UserProfile.user_id)
            .where(and_(*search_conditions))
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        search_query = search_query.offset((page - 1) * size).limit(size)
        search_query = search_query.order_by(desc(UserProfile.last_active))

        result = await self.db.execute(search_query)
        users = result.scalars().all()

        # Log search
        if user_id:
            await self._log_search(user_id, query, "user", len(users))

        return users, total

    # === ACTIVITY FEED ===

    async def create_activity(self, activity_data: ActivityData) -> UserActivity:
        """Create a new user activity"""

        activity = UserActivity(
            user_id=activity_data.user_id,
            activity_type=activity_data.activity_type,
            title=activity_data.title,
            description=activity_data.description,
            metadata=activity_data.metadata,
            is_public=activity_data.is_public,
            is_featured=activity_data.is_featured,
        )

        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)

        logger.info(
            "Activity created",
            user_id=activity_data.user_id,
            activity_type=activity_data.activity_type,
        )
        return activity

    async def get_user_activities(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
        filters: Optional[ActivityFilters] = None,
    ) -> Tuple[List[UserActivity], int]:
        """Get user's activities"""

        query = select(UserActivity).where(UserActivity.user_id == user_id)

        # Apply filters
        if filters:
            if filters.activity_type:
                query = query.where(UserActivity.activity_type == filters.activity_type)
            if filters.is_public is not None:
                query = query.where(UserActivity.is_public == filters.is_public)
            if filters.is_featured is not None:
                query = query.where(UserActivity.is_featured == filters.is_featured)
            if filters.date_from:
                query = query.where(UserActivity.created_at >= filters.date_from)
            if filters.date_to:
                query = query.where(UserActivity.created_at <= filters.date_to)

        # Count total
        total_query = select(func.count(UserActivity.id)).where(
            UserActivity.user_id == user_id
        )
        if filters:
            if filters.activity_type:
                total_query = total_query.where(
                    UserActivity.activity_type == filters.activity_type
                )
            if filters.is_public is not None:
                total_query = total_query.where(
                    UserActivity.is_public == filters.is_public
                )
            if filters.is_featured is not None:
                total_query = total_query.where(
                    UserActivity.is_featured == filters.is_featured
                )
            if filters.date_from:
                total_query = total_query.where(
                    UserActivity.created_at >= filters.date_from
                )
            if filters.date_to:
                total_query = total_query.where(
                    UserActivity.created_at <= filters.date_to
                )

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = query.offset((page - 1) * size).limit(size)
        query = query.order_by(desc(UserActivity.created_at))

        result = await self.db.execute(query)
        activities = result.scalars().all()

        return activities, total

    async def get_friends_activities(
        self, user_id: int, page: int = 1, size: int = 20
    ) -> Tuple[List[UserActivity], int]:
        """Get friends' activities"""

        # Get user's friends
        friends_query = select(Friendship).where(
            and_(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == FriendshipStatus.ACCEPTED,
            )
        )
        friends_result = await self.db.execute(friends_query)
        friendships = friends_result.scalars().all()

        # Extract friend IDs
        friend_ids = []
        for friendship in friendships:
            if friendship.user_id == user_id:
                friend_ids.append(friendship.friend_id)
            else:
                friend_ids.append(friendship.user_id)

        if not friend_ids:
            return [], 0

        # Get friends' activities
        query = select(UserActivity).where(
            and_(UserActivity.user_id.in_(friend_ids), UserActivity.is_public == True)
        )

        # Count total
        total_query = select(func.count(UserActivity.id)).where(
            and_(UserActivity.user_id.in_(friend_ids), UserActivity.is_public == True)
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = query.offset((page - 1) * size).limit(size)
        query = query.order_by(desc(UserActivity.created_at))

        result = await self.db.execute(query)
        activities = result.scalars().all()

        return activities, total

    # === NOTIFICATIONS ===

    async def create_notification(
        self, notification_data: NotificationData
    ) -> Notification:
        """Create a new notification"""

        notification = Notification(
            user_id=notification_data.user_id,
            notification_type=notification_data.notification_type,
            title=notification_data.title,
            message=notification_data.message,
            action_url=notification_data.action_url,
            metadata=notification_data.metadata,
            is_important=notification_data.is_important,
            expires_at=notification_data.expires_at,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        logger.info(
            "Notification created",
            user_id=notification_data.user_id,
            notification_type=notification_data.notification_type,
        )
        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
        filters: Optional[NotificationFilters] = None,
    ) -> Tuple[List[Notification], int, int]:
        """Get user's notifications"""

        query = select(Notification).where(Notification.user_id == user_id)

        # Apply filters
        if filters:
            if filters.notification_type:
                query = query.where(
                    Notification.notification_type == filters.notification_type
                )
            if filters.is_read is not None:
                query = query.where(Notification.is_read == filters.is_read)
            if filters.is_important is not None:
                query = query.where(Notification.is_important == filters.is_important)
            if filters.date_from:
                query = query.where(Notification.created_at >= filters.date_from)
            if filters.date_to:
                query = query.where(Notification.created_at <= filters.date_to)

        # Count total
        total_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id
        )
        if filters:
            if filters.notification_type:
                total_query = total_query.where(
                    Notification.notification_type == filters.notification_type
                )
            if filters.is_read is not None:
                total_query = total_query.where(Notification.is_read == filters.is_read)
            if filters.is_important is not None:
                total_query = total_query.where(
                    Notification.is_important == filters.is_important
                )
            if filters.date_from:
                total_query = total_query.where(
                    Notification.created_at >= filters.date_from
                )
            if filters.date_to:
                total_query = total_query.where(
                    Notification.created_at <= filters.date_to
                )

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Count unread
        unread_query = select(func.count(Notification.id)).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        unread_result = await self.db.execute(unread_query)
        unread_count = unread_result.scalar_one()

        # Apply pagination and ordering
        query = query.offset((page - 1) * size).limit(size)
        query = query.order_by(desc(Notification.created_at))

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        return notifications, total, unread_count

    async def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""

        notification = await self.db.get(Notification, notification_id)
        if not notification or notification.user_id != user_id:
            raise NotificationNotFoundError("Notification not found")

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()

        logger.info(
            "Notification marked as read",
            notification_id=notification_id,
            user_id=user_id,
        )
        return True

    async def mark_all_notifications_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""

        result = await self.db.execute(
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.is_read == False))
            .values(is_read=True, read_at=datetime.utcnow())
        )

        await self.db.commit()

        logger.info(
            "All notifications marked as read", user_id=user_id, count=result.rowcount
        )
        return result.rowcount

    # === ACHIEVEMENTS ===

    async def unlock_achievement(
        self, achievement_data: AchievementData
    ) -> UserAchievement:
        """Unlock an achievement for a user"""

        # Check if achievement already exists
        existing_achievement = await self.db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == achievement_data.user_id,
                    UserAchievement.achievement_type
                    == achievement_data.achievement_type,
                )
            )
        )
        if existing_achievement.scalar_one_or_none():
            raise ValidationError("Achievement already unlocked")

        # Create achievement
        achievement = UserAchievement(
            user_id=achievement_data.user_id,
            achievement_type=achievement_data.achievement_type,
            title=achievement_data.title,
            description=achievement_data.description,
            icon_url=achievement_data.icon_url,
            points=achievement_data.points,
            rarity=achievement_data.rarity,
            category=achievement_data.category,
        )

        self.db.add(achievement)
        await self.db.commit()
        await self.db.refresh(achievement)

        # Create notification
        await self._create_notification(
            user_id=achievement_data.user_id,
            notification_type=NotificationType.ACHIEVEMENT_UNLOCKED,
            title="Achievement Unlocked!",
            message=f"You've unlocked the achievement: {achievement_data.title}",
            metadata={
                "achievement_id": achievement.id,
                "points": achievement_data.points,
            },
        )

        logger.info(
            "Achievement unlocked",
            user_id=achievement_data.user_id,
            achievement_type=achievement_data.achievement_type,
        )
        return achievement

    # === LEADERBOARDS ===

    async def get_leaderboard(
        self,
        category: str,
        time_period: str = "all_time",
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[LeaderboardEntry], int]:
        """Get leaderboard entries"""

        # Get leaderboard
        leaderboard_query = select(Leaderboard).where(
            and_(
                Leaderboard.category == category,
                Leaderboard.time_period == time_period,
                Leaderboard.is_active == True,
            )
        )
        leaderboard_result = await self.db.execute(leaderboard_query)
        leaderboard = leaderboard_result.scalar_one_or_none()

        if not leaderboard:
            return [], 0

        # Get entries
        query = select(LeaderboardEntry).where(
            LeaderboardEntry.leaderboard_id == leaderboard.id
        )

        # Count total
        total_query = select(func.count(LeaderboardEntry.id)).where(
            LeaderboardEntry.leaderboard_id == leaderboard.id
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = query.offset((page - 1) * size).limit(size)
        query = query.order_by(asc(LeaderboardEntry.rank))
        query = query.options(selectinload(LeaderboardEntry.user))

        result = await self.db.execute(query)
        entries = result.scalars().all()

        return entries, total

    # === UTILITY METHODS ===

    async def _get_friendship(
        self, user_id: int, friend_id: int
    ) -> Optional[Friendship]:
        """Get friendship between two users"""
        result = await self.db.execute(
            select(Friendship).where(
                and_(
                    or_(
                        and_(
                            Friendship.user_id == user_id,
                            Friendship.friend_id == friend_id,
                        ),
                        and_(
                            Friendship.user_id == friend_id,
                            Friendship.friend_id == user_id,
                        ),
                    )
                )
            )
        )
        return result.scalar_one_or_none()

    async def _update_friend_counts(
        self, user_id: int, friend_id: int, increment: bool
    ):
        """Update friend counts for both users"""
        # This would be implemented to update friend counts
        pass

    async def _create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create a notification for a user"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            metadata=metadata,
        )
        self.db.add(notification)
        await self.db.commit()

    async def _log_search(
        self, user_id: int, query: str, search_type: str, results_count: int
    ):
        """Log user search for analytics"""
        search_log = UserSearch(
            user_id=user_id,
            query=query,
            search_type=search_type,
            results_count=results_count,
        )
        self.db.add(search_log)
        await self.db.commit()
