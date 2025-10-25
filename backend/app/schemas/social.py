"""
Social schemas for GambleGlee
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class FriendshipStatus(str, Enum):
    """Friendship status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    DECLINED = "declined"

class NotificationType(str, Enum):
    """Notification type enumeration"""
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    BET_INVITATION = "bet_invitation"
    BET_ACCEPTED = "bet_accepted"
    BET_RESOLVED = "bet_resolved"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    TRICK_SHOT_LIKED = "trick_shot_liked"
    TRICK_SHOT_COMMENTED = "trick_shot_commented"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SECURITY_ALERT = "security_alert"

class ActivityType(str, Enum):
    """Activity type enumeration"""
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    BET_CREATED = "bet_created"
    BET_ACCEPTED = "bet_accepted"
    BET_RESOLVED = "bet_resolved"
    BET_WON = "bet_won"
    BET_LOST = "bet_lost"
    TRICK_SHOT_CREATED = "trick_shot_created"
    TRICK_SHOT_COMPLETED = "trick_shot_completed"
    FRIEND_ADDED = "friend_added"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    PROFILE_UPDATED = "profile_updated"

class PrivacyLevel(str, Enum):
    """Privacy level enumeration"""
    PUBLIC = "public"
    FRIENDS_ONLY = "friends_only"
    PRIVATE = "private"

# === REQUEST SCHEMAS ===

class FriendRequestRequest(BaseModel):
    """Friend request request"""
    friend_id: int = Field(..., gt=0, description="ID of the user to send friend request to")
    message: Optional[str] = Field(None, max_length=500, description="Optional message with friend request")

class FriendRequestResponse(BaseModel):
    """Friend request response"""
    friend_id: int = Field(..., gt=0, description="ID of the user to respond to")
    action: str = Field(..., description="Action to take: accept, decline, block")

class UserSearchRequest(BaseModel):
    """User search request"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    search_type: str = Field("user", description="Type of search: user, bet, trick_shot")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=50, description="Page size")

class ActivityCreateRequest(BaseModel):
    """Activity creation request"""
    activity_type: ActivityType = Field(..., description="Type of activity")
    title: str = Field(..., min_length=1, max_length=255, description="Activity title")
    description: Optional[str] = Field(None, max_length=1000, description="Activity description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Activity metadata")
    is_public: bool = Field(True, description="Whether activity is public")

class NotificationCreateRequest(BaseModel):
    """Notification creation request"""
    user_id: int = Field(..., gt=0, description="User ID to send notification to")
    notification_type: NotificationType = Field(..., description="Type of notification")
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    action_url: Optional[str] = Field(None, max_length=500, description="Action URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Notification metadata")
    is_important: bool = Field(False, description="Whether notification is important")

class ProfileUpdateRequest(BaseModel):
    """Profile update request"""
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    location: Optional[str] = Field(None, max_length=100, description="User location")
    website: Optional[str] = Field(None, max_length=255, description="User website")
    privacy_level: Optional[PrivacyLevel] = Field(None, description="Privacy level")
    show_online_status: Optional[bool] = Field(None, description="Show online status")
    show_activity: Optional[bool] = Field(None, description="Show activity")
    allow_friend_requests: Optional[bool] = Field(None, description="Allow friend requests")
    allow_messages: Optional[bool] = Field(None, description="Allow messages")

class CommentCreateRequest(BaseModel):
    """Comment creation request"""
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")
    parent_comment_id: Optional[int] = Field(None, gt=0, description="Parent comment ID for replies")

class LeaderboardRequest(BaseModel):
    """Leaderboard request"""
    category: str = Field(..., description="Leaderboard category")
    time_period: str = Field("all_time", description="Time period: daily, weekly, monthly, all_time")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")

# === RESPONSE SCHEMAS ===

class UserProfileResponse(BaseModel):
    """User profile response"""
    id: int
    user_id: int
    bio: Optional[str]
    location: Optional[str]
    website: Optional[str]
    birth_date: Optional[datetime]
    gender: Optional[str]
    privacy_level: PrivacyLevel
    show_online_status: bool
    show_activity: bool
    allow_friend_requests: bool
    allow_messages: bool
    total_bets: int
    won_bets: int
    lost_bets: int
    total_winnings: float
    total_losses: float
    win_rate: float
    trick_shots_created: int
    trick_shots_completed: int
    trick_shots_liked: int
    trick_shots_commented: int
    friends_count: int
    followers_count: int
    following_count: int
    created_at: datetime
    updated_at: datetime
    last_active: Optional[datetime]

    class Config:
        from_attributes = True

class FriendshipResponse(BaseModel):
    """Friendship response"""
    id: int
    user_id: int
    friend_id: int
    status: FriendshipStatus
    initiated_by: int
    is_favorite: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserActivityResponse(BaseModel):
    """User activity response"""
    id: int
    user_id: int
    activity_type: ActivityType
    title: str
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]
    is_public: bool
    is_featured: bool
    likes_count: int
    comments_count: int
    shares_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ActivityLikeResponse(BaseModel):
    """Activity like response"""
    id: int
    activity_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ActivityCommentResponse(BaseModel):
    """Activity comment response"""
    id: int
    activity_id: int
    user_id: int
    content: str
    parent_comment_id: Optional[int]
    is_edited: bool
    edited_at: Optional[datetime]
    likes_count: int
    replies_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    """Notification response"""
    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    is_important: bool
    action_url: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    read_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserAchievementResponse(BaseModel):
    """User achievement response"""
    id: int
    user_id: int
    achievement_type: str
    title: str
    description: Optional[str]
    icon_url: Optional[str]
    points: int
    rarity: str
    category: str
    unlocked_at: datetime

    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    """Leaderboard response"""
    id: int
    name: str
    description: Optional[str]
    category: str
    metric: str
    time_period: str
    max_entries: int
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True

class LeaderboardEntryResponse(BaseModel):
    """Leaderboard entry response"""
    id: int
    leaderboard_id: int
    user_id: int
    rank: int
    score: float
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserSearchResponse(BaseModel):
    """User search response"""
    id: int
    username: str
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    is_online: bool
    last_active: Optional[datetime]
    friends_count: int
    total_bets: int
    win_rate: float
    is_friend: bool
    friendship_status: Optional[FriendshipStatus]

    class Config:
        from_attributes = True

class UserSearchListResponse(BaseModel):
    """User search list response"""
    items: List[UserSearchResponse]
    total: int
    page: int
    size: int
    pages: int

class ActivityListResponse(BaseModel):
    """Activity list response"""
    items: List[UserActivityResponse]
    total: int
    page: int
    size: int
    pages: int

class NotificationListResponse(BaseModel):
    """Notification list response"""
    items: List[NotificationResponse]
    total: int
    page: int
    size: int
    pages: int
    unread_count: int

class LeaderboardListResponse(BaseModel):
    """Leaderboard list response"""
    items: List[LeaderboardEntryResponse]
    total: int
    page: int
    size: int
    pages: int

class FriendshipListResponse(BaseModel):
    """Friendship list response"""
    items: List[FriendshipResponse]
    total: int
    page: int
    size: int
    pages: int

class UserStatsResponse(BaseModel):
    """User statistics response"""
    total_bets: int
    won_bets: int
    lost_bets: int
    total_winnings: float
    total_losses: float
    win_rate: float
    trick_shots_created: int
    trick_shots_completed: int
    friends_count: int
    followers_count: int
    following_count: int
    achievements_count: int
    total_points: int

class SocialDashboardResponse(BaseModel):
    """Social dashboard response"""
    user_profile: UserProfileResponse
    recent_activities: List[UserActivityResponse]
    friends_activities: List[UserActivityResponse]
    notifications: List[NotificationResponse]
    achievements: List[UserAchievementResponse]
    leaderboard_position: Optional[LeaderboardEntryResponse]
    stats: UserStatsResponse

# === INTERNAL SCHEMAS ===

class FriendshipData(BaseModel):
    """Friendship data schema"""
    user_id: int
    friend_id: int
    status: FriendshipStatus
    initiated_by: int
    is_favorite: bool = False
    notes: Optional[str] = None

class ActivityData(BaseModel):
    """Activity data schema"""
    user_id: int
    activity_type: ActivityType
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_public: bool = True
    is_featured: bool = False

class NotificationData(BaseModel):
    """Notification data schema"""
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_important: bool = False
    expires_at: Optional[datetime] = None

class AchievementData(BaseModel):
    """Achievement data schema"""
    user_id: int
    achievement_type: str
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    points: int = 0
    rarity: str = "common"
    category: str

class LeaderboardData(BaseModel):
    """Leaderboard data schema"""
    name: str
    description: Optional[str] = None
    category: str
    metric: str
    time_period: str = "all_time"
    max_entries: int = 100
    is_active: bool = True
    is_public: bool = True

class LeaderboardEntryData(BaseModel):
    """Leaderboard entry data schema"""
    leaderboard_id: int
    user_id: int
    rank: int
    score: float
    metadata: Optional[Dict[str, Any]] = None

# === VALIDATION SCHEMAS ===

class UserSearchFilters(BaseModel):
    """User search filters"""
    location: Optional[str] = None
    min_friends: Optional[int] = None
    max_friends: Optional[int] = None
    min_win_rate: Optional[float] = None
    max_win_rate: Optional[float] = None
    is_online: Optional[bool] = None
    has_avatar: Optional[bool] = None

class ActivityFilters(BaseModel):
    """Activity filters"""
    activity_type: Optional[ActivityType] = None
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[int] = None

class NotificationFilters(BaseModel):
    """Notification filters"""
    notification_type: Optional[NotificationType] = None
    is_read: Optional[bool] = None
    is_important: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
