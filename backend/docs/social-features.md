# Social Features Documentation

## Overview

The GambleGlee social system provides comprehensive user interaction features including friend management, user search, activity feeds, notifications, and leaderboards. This system enables users to connect, share activities, and compete in a social betting environment.

## Features

### Friend System
- **Friend Requests**: Send, accept, decline, and block friend requests
- **Friend Management**: Add, remove, and manage friends
- **Friend Lists**: View friends with pagination and filtering
- **Friend Status**: Track friendship status and relationships

### User Search
- **Advanced Search**: Search users by username, display name, location
- **Search Filters**: Filter by location, friend count, win rate, online status
- **Search Analytics**: Track search patterns and results
- **User Discovery**: Find new friends and opponents

### Activity Feed
- **User Activities**: Track user actions and achievements
- **Friends Activities**: See friends' activities and updates
- **Activity Types**: Betting, trick shots, social interactions
- **Activity Privacy**: Control activity visibility

### Notifications
- **Real-time Notifications**: Friend requests, bet updates, achievements
- **Notification Types**: Various notification categories
- **Notification Management**: Mark as read, delete, filter
- **Notification Preferences**: Customize notification settings

### Leaderboards
- **Multiple Categories**: Betting, trick shots, social, general
- **Time Periods**: Daily, weekly, monthly, all-time
- **Ranking System**: Competitive rankings and scores
- **Achievement System**: Unlock achievements and rewards

## API Endpoints

### Friend System Endpoints

#### POST `/api/v1/social/friends/request`
Send a friend request to another user.

**Request Body:**
```json
{
  "friend_id": 123,
  "message": "Let's be friends!"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "friend_id": 123,
  "status": "pending",
  "initiated_by": 1,
  "is_favorite": false,
  "notes": "Let's be friends!",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "accepted_at": null
}
```

#### POST `/api/v1/social/friends/respond`
Respond to a friend request.

**Request Body:**
```json
{
  "friend_id": 1,
  "action": "accept"
}
```

**Actions:**
- `accept`: Accept the friend request
- `decline`: Decline the friend request
- `block`: Block the user

#### DELETE `/api/v1/social/friends/{friend_id}`
Remove a friend.

**Response:**
```json
{
  "message": "Friend removed successfully"
}
```

#### POST `/api/v1/social/friends/{friend_id}/block`
Block a user.

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "friend_id": 123,
  "status": "blocked",
  "initiated_by": 1,
  "is_favorite": false,
  "notes": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "accepted_at": null
}
```

#### GET `/api/v1/social/friends`
Get user's friends list.

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Page size (default: 20, max: 100)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "friend_id": 123,
      "status": "accepted",
      "initiated_by": 1,
      "is_favorite": false,
      "notes": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "accepted_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

#### GET `/api/v1/social/friends/requests`
Get pending friend requests.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 123,
      "friend_id": 1,
      "status": "pending",
      "initiated_by": 123,
      "is_favorite": false,
      "notes": "Let's be friends!",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "accepted_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

### User Search Endpoints

#### POST `/api/v1/social/search/users`
Search for users.

**Request Body:**
```json
{
  "query": "john",
  "search_type": "user",
  "filters": {
    "location": "New York",
    "min_friends": 0,
    "max_friends": 100,
    "min_win_rate": 0.0,
    "max_win_rate": 1.0,
    "is_online": true,
    "has_avatar": true
  },
  "page": 1,
  "size": 10
}
```

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "username": "john_doe",
      "display_name": "John Doe",
      "avatar_url": "https://example.com/avatar.jpg",
      "bio": "Betting enthusiast",
      "location": "New York",
      "is_online": true,
      "last_active": "2024-01-01T00:00:00Z",
      "friends_count": 50,
      "total_bets": 100,
      "win_rate": 0.65,
      "is_friend": false,
      "friendship_status": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### Activity Feed Endpoints

#### POST `/api/v1/social/activities`
Create a new activity.

**Request Body:**
```json
{
  "activity_type": "bet_created",
  "title": "Created a new bet",
  "description": "I created a bet on the game",
  "metadata": {
    "bet_id": 123,
    "amount": 50.0
  },
  "is_public": true
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "activity_type": "bet_created",
  "title": "Created a new bet",
  "description": "I created a bet on the game",
  "metadata": {
    "bet_id": 123,
    "amount": 50.0
  },
  "is_public": true,
  "is_featured": false,
  "likes_count": 0,
  "comments_count": 0,
  "shares_count": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### GET `/api/v1/social/activities`
Get user's activities.

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Page size (default: 20, max: 100)
- `activity_type`: Filter by activity type
- `is_public`: Filter by public status
- `is_featured`: Filter by featured status

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "activity_type": "bet_created",
      "title": "Created a new bet",
      "description": "I created a bet on the game",
      "metadata": {
        "bet_id": 123,
        "amount": 50.0
      },
      "is_public": true,
      "is_featured": false,
      "likes_count": 5,
      "comments_count": 2,
      "shares_count": 1,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

#### GET `/api/v1/social/activities/friends`
Get friends' activities.

**Response:**
```json
{
  "items": [
    {
      "id": 2,
      "user_id": 123,
      "activity_type": "bet_won",
      "title": "Won a bet!",
      "description": "I won $100 on my bet",
      "metadata": {
        "bet_id": 456,
        "amount": 100.0
      },
      "is_public": true,
      "is_featured": false,
      "likes_count": 10,
      "comments_count": 5,
      "shares_count": 2,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

### Notification Endpoints

#### GET `/api/v1/social/notifications`
Get user's notifications.

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Page size (default: 20, max: 100)
- `notification_type`: Filter by notification type
- `is_read`: Filter by read status
- `is_important`: Filter by importance

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "notification_type": "friend_request",
      "title": "New Friend Request",
      "message": "You have a new friend request from John Doe",
      "is_read": false,
      "is_important": false,
      "action_url": "/friends/requests",
      "metadata": {
        "friendship_id": 1,
        "requester_id": 123
      },
      "created_at": "2024-01-01T00:00:00Z",
      "read_at": null,
      "expires_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1,
  "unread_count": 1
}
```

#### POST `/api/v1/social/notifications/{notification_id}/read`
Mark a notification as read.

**Response:**
```json
{
  "message": "Notification marked as read"
}
```

#### POST `/api/v1/social/notifications/read-all`
Mark all notifications as read.

**Response:**
```json
{
  "message": "Marked 5 notifications as read"
}
```

### Leaderboard Endpoints

#### GET `/api/v1/social/leaderboards/{category}`
Get leaderboard entries.

**Path Parameters:**
- `category`: Leaderboard category (betting, trick_shot, social, general)

**Query Parameters:**
- `time_period`: Time period (daily, weekly, monthly, all_time)
- `page`: Page number (default: 1)
- `size`: Page size (default: 20, max: 100)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "leaderboard_id": 1,
      "user_id": 123,
      "rank": 1,
      "score": 95.5,
      "metadata": {
        "win_rate": 0.95,
        "total_bets": 100,
        "total_winnings": 5000.0
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

### Dashboard Endpoint

#### GET `/api/v1/social/dashboard`
Get social dashboard data.

**Response:**
```json
{
  "user_profile": {
    "id": 1,
    "user_id": 1,
    "bio": "Betting enthusiast",
    "location": "New York",
    "website": "https://example.com",
    "privacy_level": "public",
    "show_online_status": true,
    "show_activity": true,
    "allow_friend_requests": true,
    "allow_messages": true,
    "total_bets": 100,
    "won_bets": 65,
    "lost_bets": 35,
    "total_winnings": 5000.0,
    "total_losses": 2000.0,
    "win_rate": 0.65,
    "trick_shots_created": 10,
    "trick_shots_completed": 8,
    "friends_count": 50,
    "followers_count": 100,
    "following_count": 75,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_active": "2024-01-01T00:00:00Z"
  },
  "recent_activities": [
    {
      "id": 1,
      "user_id": 1,
      "activity_type": "bet_created",
      "title": "Created a new bet",
      "description": "I created a bet on the game",
      "metadata": {
        "bet_id": 123,
        "amount": 50.0
      },
      "is_public": true,
      "is_featured": false,
      "likes_count": 5,
      "comments_count": 2,
      "shares_count": 1,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "friends_activities": [
    {
      "id": 2,
      "user_id": 123,
      "activity_type": "bet_won",
      "title": "Won a bet!",
      "description": "I won $100 on my bet",
      "metadata": {
        "bet_id": 456,
        "amount": 100.0
      },
      "is_public": true,
      "is_featured": false,
      "likes_count": 10,
      "comments_count": 5,
      "shares_count": 2,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "notifications": [
    {
      "id": 1,
      "user_id": 1,
      "notification_type": "friend_request",
      "title": "New Friend Request",
      "message": "You have a new friend request from John Doe",
      "is_read": false,
      "is_important": false,
      "action_url": "/friends/requests",
      "metadata": {
        "friendship_id": 1,
        "requester_id": 123
      },
      "created_at": "2024-01-01T00:00:00Z",
      "read_at": null,
      "expires_at": null
    }
  ],
  "achievements": [
    {
      "id": 1,
      "user_id": 1,
      "achievement_type": "first_bet",
      "title": "First Bet",
      "description": "Placed your first bet",
      "icon_url": "https://example.com/achievement.jpg",
      "points": 10,
      "rarity": "common",
      "category": "betting",
      "unlocked_at": "2024-01-01T00:00:00Z"
    }
  ],
  "leaderboard_position": {
    "id": 1,
    "leaderboard_id": 1,
    "user_id": 1,
    "rank": 15,
    "score": 85.5,
    "metadata": {
      "win_rate": 0.85,
      "total_bets": 50,
      "total_winnings": 2500.0
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "stats": {
    "total_bets": 100,
    "won_bets": 65,
    "lost_bets": 35,
    "total_winnings": 5000.0,
    "total_losses": 2000.0,
    "win_rate": 0.65,
    "trick_shots_created": 10,
    "trick_shots_completed": 8,
    "friends_count": 50,
    "followers_count": 100,
    "following_count": 75,
    "achievements_count": 5,
    "total_points": 250
  }
}
```

## Data Models

### User Profile
- **Basic Info**: Bio, location, website, birth date, gender
- **Privacy Settings**: Privacy level, online status, activity visibility
- **Statistics**: Betting stats, trick shot stats, social stats
- **Preferences**: Notification settings, friend request settings

### Friendship
- **Status**: Pending, accepted, blocked, declined
- **Metadata**: Initiated by, notes, favorite status
- **Timestamps**: Created, updated, accepted

### User Activity
- **Activity Types**: Betting, trick shots, social interactions
- **Content**: Title, description, metadata
- **Engagement**: Likes, comments, shares
- **Privacy**: Public/private visibility

### Notification
- **Types**: Friend requests, bet updates, achievements
- **Content**: Title, message, action URL
- **Status**: Read/unread, important flag
- **Metadata**: Additional data for the notification

### Achievement
- **Types**: Betting, social, trick shot, general
- **Rarity**: Common, rare, epic, legendary
- **Rewards**: Points, badges, titles
- **Categories**: Organized by activity type

### Leaderboard
- **Categories**: Betting, trick shots, social, general
- **Metrics**: Win rate, total winnings, friends count
- **Time Periods**: Daily, weekly, monthly, all-time
- **Rankings**: Competitive leaderboard positions

## Privacy and Security

### Privacy Levels
- **Public**: Visible to everyone
- **Friends Only**: Visible to friends only
- **Private**: Visible to user only

### Data Protection
- **User Consent**: Explicit consent for data sharing
- **Data Minimization**: Only collect necessary data
- **Access Control**: User controls data visibility
- **Data Retention**: Automatic data cleanup

### Security Features
- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Prevent abuse and spam
- **Content Moderation**: Filter inappropriate content
- **Audit Logging**: Track all social interactions

## Performance Optimization

### Caching Strategy
- **Redis Caching**: Cache frequently accessed data
- **Query Optimization**: Optimize database queries
- **Pagination**: Efficient data loading
- **CDN Integration**: Fast content delivery

### Database Optimization
- **Indexing**: Optimize database indexes
- **Query Optimization**: Efficient SQL queries
- **Connection Pooling**: Manage database connections
- **Read Replicas**: Distribute read load

### Real-time Features
- **WebSocket Integration**: Real-time notifications
- **Event Streaming**: Activity feed updates
- **Push Notifications**: Mobile notifications
- **Live Updates**: Real-time leaderboard updates

## Monitoring and Analytics

### Metrics Tracking
- **User Engagement**: Activity levels, friend connections
- **Content Performance**: Popular activities, engagement rates
- **Search Analytics**: Search patterns, result effectiveness
- **Notification Metrics**: Delivery rates, engagement

### Performance Monitoring
- **Response Times**: API endpoint performance
- **Database Performance**: Query execution times
- **Cache Hit Rates**: Caching effectiveness
- **Error Rates**: System reliability

### Business Intelligence
- **User Behavior**: Social interaction patterns
- **Content Trends**: Popular activity types
- **Engagement Metrics**: User retention and activity
- **Growth Metrics**: User acquisition and engagement

## Troubleshooting

### Common Issues

#### "Friend request already sent"
- User has already sent a friend request
- Solution: Check existing friendship status

#### "Cannot send friend request to yourself"
- User is trying to friend themselves
- Solution: Use different user ID

#### "User not found"
- Friend ID doesn't exist
- Solution: Verify user exists

#### "Friendship not found"
- No friendship relationship exists
- Solution: Send friend request first

#### "Notification not found"
- Notification ID doesn't exist
- Solution: Verify notification exists

### Error Codes
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Support
For social features issues, contact support with:
- User ID and friend ID
- Error message and timestamp
- Steps to reproduce
- Browser/device information
- Screenshots if applicable
