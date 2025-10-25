# Authentication System Documentation

## Overview

The GambleGlee authentication system provides comprehensive user management, security features, and session handling. It supports multiple authentication methods, two-factor authentication, and advanced security features.

## Features

### Core Authentication
- **User Registration**: Email/password signup with validation
- **User Login**: JWT-based authentication with session management
- **Email Verification**: Account verification via email
- **Password Reset**: Secure password recovery system
- **Session Management**: Multi-device session tracking
- **Logout**: Single device or all devices logout

### Security Features
- **Password Security**: Strong password requirements
- **Account Lockout**: Protection against brute force attacks
- **Two-Factor Authentication**: TOTP-based 2FA with backup codes
- **Device Management**: Trusted device tracking
- **Login History**: Security audit trail
- **Risk Assessment**: Automated risk scoring

### Advanced Features
- **OAuth Integration**: Google, Facebook, Apple, GitHub
- **Social Login**: Seamless third-party authentication
- **Device Fingerprinting**: Security tracking
- **Geolocation**: Location-based security
- **Rate Limiting**: API protection

## API Endpoints

### Authentication Endpoints

#### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "SecurePassword123",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe",
  "marketing_emails": false
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "username",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "is_active": false,
    "is_verified": false,
    "role": "user",
    "status": "pending",
    "auth_provider": "email",
    "two_factor_enabled": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### POST `/api/v1/auth/login`
Authenticate user and create session.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "remember_me": false,
  "device_name": "Chrome Browser",
  "device_type": "desktop"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "is_active": true,
    "is_verified": true,
    "role": "user",
    "status": "active",
    "last_login_at": "2024-01-01T00:00:00Z"
  }
}
```

#### POST `/api/v1/auth/refresh`
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST `/api/v1/auth/logout`
Logout user from session(s).

**Request Body:**
```json
{
  "session_id": "optional-session-id",
  "logout_all": false
}
```

**Response:**
```json
{
  "message": "Logged out successfully",
  "sessions_logged_out": 1
}
```

### User Management Endpoints

#### GET `/api/v1/auth/me`
Get current user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "username",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe",
  "bio": "User bio",
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true,
  "is_verified": true,
  "role": "user",
  "status": "active",
  "auth_provider": "email",
  "two_factor_enabled": false,
  "privacy_level": "public",
  "email_notifications": true,
  "push_notifications": true,
  "marketing_emails": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "verified_at": "2024-01-01T00:00:00Z",
  "last_login_at": "2024-01-01T00:00:00Z",
  "login_count": 5
}
```

### Email Verification Endpoints

#### POST `/api/v1/auth/verify-email`
Verify user email address.

**Request Body:**
```json
{
  "token": "verification-token"
}
```

**Response:**
```json
{
  "message": "Email verified successfully",
  "expires_in": 0
}
```

#### POST `/api/v1/auth/resend-verification`
Resend verification email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Verification email sent",
  "expires_in": 86400
}
```

### Password Management Endpoints

#### POST `/api/v1/auth/forgot-password`
Request password reset.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset email sent",
  "expires_in": 3600
}
```

#### POST `/api/v1/auth/reset-password`
Reset password using token.

**Request Body:**
```json
{
  "token": "reset-token",
  "new_password": "NewSecurePassword123"
}
```

**Response:**
```json
{
  "message": "Password reset successfully",
  "expires_in": 0
}
```

#### POST `/api/v1/auth/change-password`
Change user password.

**Request Body:**
```json
{
  "current_password": "CurrentPassword123",
  "new_password": "NewSecurePassword123"
}
```

**Response:**
```json
{
  "message": "Password changed successfully",
  "expires_in": 0
}
```

### Validation Endpoints

#### POST `/api/v1/auth/check-username`
Check username availability.

**Request Body:**
```json
{
  "username": "desired_username"
}
```

**Response:**
```json
{
  "available": true,
  "message": "Username is available"
}
```

#### POST `/api/v1/auth/check-email`
Check email availability.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "available": true,
  "message": "Email is available"
}
```

## Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- Optional special characters

### Account Security
- **Account Lockout**: 5 failed login attempts lock account for 30 minutes
- **Session Management**: 30-minute timeout, 30-day refresh token expiry
- **Device Tracking**: Track and manage trusted devices
- **Login History**: Audit trail of all login attempts

### Two-Factor Authentication
- **TOTP Support**: Google Authenticator, Authy, etc.
- **Backup Codes**: 10 single-use backup codes
- **QR Code Generation**: Easy setup process
- **Recovery Process**: Secure account recovery

### Risk Assessment
- **IP Analysis**: Suspicious IP detection
- **Device Fingerprinting**: Unique device identification
- **Behavioral Analysis**: Unusual activity detection
- **Geolocation**: Location-based security

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Invalid credentials"
}
```

#### 403 Forbidden
```json
{
  "detail": "Account is locked"
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

#### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

### Default Limits
- **Registration**: 5 attempts per 5 minutes
- **Login**: 10 attempts per 5 minutes
- **Password Reset**: 3 attempts per hour
- **Email Verification**: 5 attempts per hour
- **Username/Email Check**: 20 attempts per minute

### Progressive Penalties
- **First Violation**: Warning
- **Second Violation**: 5-minute cooldown
- **Third Violation**: 15-minute cooldown
- **Fourth Violation**: 1-hour cooldown
- **Fifth Violation**: 24-hour cooldown

## Best Practices

### Client Implementation
1. **Token Storage**: Store tokens securely (httpOnly cookies recommended)
2. **Token Refresh**: Implement automatic token refresh
3. **Error Handling**: Handle authentication errors gracefully
4. **Session Management**: Implement proper logout functionality
5. **Security Headers**: Include security headers in requests

### Server Configuration
1. **Environment Variables**: Use secure environment variables
2. **HTTPS Only**: Enforce HTTPS in production
3. **CORS Configuration**: Configure CORS properly
4. **Rate Limiting**: Implement rate limiting
5. **Monitoring**: Monitor authentication events

### Security Considerations
1. **Password Hashing**: Use bcrypt with appropriate rounds
2. **Token Security**: Use secure random tokens
3. **Session Security**: Implement secure session management
4. **Audit Logging**: Log all authentication events
5. **Regular Updates**: Keep dependencies updated

## Testing

### Unit Tests
- User registration validation
- Login authentication
- Token generation and validation
- Password hashing and verification
- Email verification process

### Integration Tests
- End-to-end authentication flow
- Session management
- Password reset process
- Two-factor authentication
- Error handling

### Security Tests
- Brute force protection
- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection

## Monitoring and Logging

### Security Events
- User registration
- Login attempts (success/failure)
- Password changes
- Email verifications
- Account lockouts
- Suspicious activity

### Metrics
- Authentication success rate
- Failed login attempts
- Account lockouts
- Password reset requests
- Two-factor authentication usage

### Alerts
- Multiple failed login attempts
- Unusual login patterns
- Account takeover attempts
- Security policy violations
- System errors

## Troubleshooting

### Common Issues

#### "Email already registered"
- User is trying to register with an existing email
- Solution: Use different email or request password reset

#### "Username already taken"
- User is trying to register with an existing username
- Solution: Choose different username

#### "Invalid credentials"
- Wrong email/password combination
- Solution: Verify credentials or reset password

#### "Account is locked"
- Too many failed login attempts
- Solution: Wait for lockout period or contact support

#### "Email not verified"
- User hasn't verified their email
- Solution: Check email for verification link

#### "Invalid or expired token"
- Token is invalid or has expired
- Solution: Request new token

### Support
For authentication issues, contact support with:
- User email/username
- Error message
- Timestamp
- Browser/device information
- Steps to reproduce
