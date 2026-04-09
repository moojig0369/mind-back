"""
Core exceptions for the application.
Custom exception classes for consistent error handling.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} with id {identifier} not found",
            status_code=404,
            detail={"resource": resource, "id": identifier},
        )


class ValidationException(AppException):
    """Invalid input data."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=422,
            detail={"field": field},
        )


class UnauthorizedException(AppException):
    """Authentication required."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            status_code=401,
        )


class ForbiddenException(AppException):
    """Access denied."""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            status_code=403,
        )


class ConflictException(AppException):
    """Resource conflict."""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=409,
        )


class ServiceUnavailableException(AppException):
    """External service unavailable."""
    
    def __init__(self, service: str):
        super().__init__(
            message=f"Service {service} is unavailable",
            status_code=503,
            detail={"service": service},
        )
