"""
Security utilities for API authentication.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings


# API Key header security scheme
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=True)


async def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate API key from request header.

    Args:
        api_key: API key from request header

    Returns:
        str: Valid API key

    Raises:
        HTTPException: If API key is invalid
    """
    valid_keys = settings.api_keys_list

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def get_optional_api_key(api_key: str = Security(api_key_header)) -> str | None:
    """
    Get API key if provided, but don't require it.
    Used for endpoints that have rate limiting based on API key.

    Args:
        api_key: API key from request header

    Returns:
        str | None: Valid API key or None
    """
    try:
        return await validate_api_key(api_key)
    except HTTPException:
        return None
