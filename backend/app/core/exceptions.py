"""
Custom exceptions for GambleGlee application
"""

from fastapi import HTTPException, status


class GambleGleeException(HTTPException):
    """Base exception for GambleGlee application"""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "GAMBLEGLEE_ERROR",
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationError(GambleGleeException):
    """Authentication related errors"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_ERROR",
        )


class AuthorizationError(GambleGleeException):
    """Authorization related errors"""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHZ_ERROR",
        )


class ValidationError(GambleGleeException):
    """Data validation errors"""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
        )


class NotFoundError(GambleGleeException):
    """Resource not found errors"""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            detail=detail, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND"
        )


class ConflictError(GambleGleeException):
    """Resource conflict errors"""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            detail=detail, status_code=status.HTTP_409_CONFLICT, error_code="CONFLICT"
        )


class InsufficientFundsError(GambleGleeException):
    """Insufficient funds errors"""

    def __init__(self, detail: str = "Insufficient funds"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INSUFFICIENT_FUNDS",
        )


class BettingError(GambleGleeException):
    """Betting related errors"""

    def __init__(self, detail: str = "Betting error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BETTING_ERROR",
        )


class ComplianceError(GambleGleeException):
    """Compliance related errors"""

    def __init__(self, detail: str = "Compliance error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="COMPLIANCE_ERROR",
        )


class SecurityError(GambleGleeException):
    """Security related errors"""

    def __init__(self, detail: str = "Security error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="SECURITY_ERROR",
        )


class AccountLockedError(GambleGleeException):
    """Account locked errors"""

    def __init__(self, detail: str = "Account is locked"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_423_LOCKED,
            error_code="ACCOUNT_LOCKED",
        )


class EmailNotVerifiedError(GambleGleeException):
    """Email not verified errors"""

    def __init__(self, detail: str = "Email not verified"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="EMAIL_NOT_VERIFIED",
        )


class UserNotFoundError(NotFoundError):
    """User not found errors"""

    def __init__(self, detail: str = "User not found"):
        super().__init__(detail=detail)


class ActivityNotFoundError(NotFoundError):
    """Activity not found errors"""

    def __init__(self, detail: str = "Activity not found"):
        super().__init__(detail=detail)


class FriendshipNotFoundError(NotFoundError):
    """Friendship not found errors"""

    def __init__(self, detail: str = "Friendship not found"):
        super().__init__(detail=detail)


class NotificationNotFoundError(NotFoundError):
    """Notification not found errors"""

    def __init__(self, detail: str = "Notification not found"):
        super().__init__(detail=detail)


class BusinessLogicError(GambleGleeException):
    """Business logic errors"""

    def __init__(self, detail: str = "Business logic error"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BUSINESS_LOGIC_ERROR",
        )
