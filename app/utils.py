"""
Utility functions including validation, error handling, and helpers.
"""

from fastapi import HTTPException, Request, status
from functools import wraps
from typing import Optional
import re
import time
from collections import defaultdict
import os


# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)


def validate_start_command(command: str) -> bool:
    """
    Validate user-provided start command for security.
    Prevents shell injection by disallowing dangerous characters and patterns.
    
    Security Rules:
    - No shell operators: &&, ||, ;, |, >, <, `
    - No command substitution: $()
    - No bash/sh execution
    - Max length: 500 characters
    """
    if not command or len(command) > 500:
        return False
    
    # Dangerous patterns that could allow shell injection
    dangerous_patterns = [
        r'&&',      # Command chaining
        r'\|\|',    # Or operator
        r';',       # Command separator
        r'\|',      # Pipe
        r'>',       # Redirect output
        r'<',       # Redirect input
        r'`',       # Command substitution
        r'\$\(',    # Command substitution
        r'bash',    # Shell execution
        r'sh ',     # Shell execution
        r'/bin/',   # Direct binary execution
        r'rm ',     # File deletion
        r'dd ',     # Disk operations
        r'mkfs',    # Format filesystem
        r'curl.*\|', # Pipe from curl
        r'wget.*\|', # Pipe from wget
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email format.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_bot_name(name: str) -> bool:
    """
    Validate bot name.
    Must be alphanumeric with hyphens/underscores, 3-50 characters.
    """
    pattern = r'^[a-zA-Z0-9_-]{3,50}$'
    return bool(re.match(pattern, name))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    Removes any path components and dangerous characters.
    """
    # Get basename to remove any path components
    filename = os.path.basename(filename)
    
    # Remove any remaining path traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Keep only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def rate_limit(requests_per_minute: int = 60):
    """
    Simple rate limiting decorator.
    In production, use Redis for distributed rate limiting.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the Request object in kwargs
            request: Optional[Request] = kwargs.get('request')
            if not request:
                # Look in args for Request
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"
                current_time = time.time()
                
                # Clean old entries
                rate_limit_storage[client_ip] = [
                    t for t in rate_limit_storage[client_ip]
                    if current_time - t < 60
                ]
                
                # Check rate limit
                if len(rate_limit_storage[client_ip]) >= requests_per_minute:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later."
                    )
                
                # Add current request
                rate_limit_storage[client_ip].append(current_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    Handles X-Forwarded-For header for proxy scenarios.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AppException(HTTPException):
    """Base exception class for application errors"""
    pass


class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ForbiddenException(AppException):
    """Access forbidden exception"""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestException(AppException):
    """Bad request exception"""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConflictException(AppException):
    """Resource conflict exception"""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
