"""API dependencies."""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import validate_api_key


async def get_current_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db():
        yield session


async def require_api_key(api_key: str = Depends(validate_api_key)) -> str:
    """Require valid API key."""
    return api_key
