from typing import Annotated, Optional
from fastapi import Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.db.models.user import User, UserRole

# Common DB Session Dependency
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.size = size


PaginationDep = Annotated[PaginationParams, Depends()]


async def get_current_user(
    db: DBSessionDep,
    x_user_id: Optional[int] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
) -> User:
    """
    Resolves the authenticated user via X-User-Id or X-User-Email header.
    Falls back to the first active Manager/Admin for local development/demonstration.
    """
    if x_user_id:
        user = await db.get(User, x_user_id)
        if not user:
            raise UnauthorizedException(f"User with ID {x_user_id} not found.")
        return user

    if x_user_email:
        result = await db.execute(select(User).where(User.email == x_user_email))
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedException(f"User with email '{x_user_email}' not found.")
        return user

    # Default fallback for development/demo: first active Manager or Admin
    result = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.role.in_([UserRole.MANAGER, UserRole.ADMIN]),
        )
    )
    user = result.scalars().first()
    if not user:
        # Fallback to any active user
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        user = result.scalars().first()

    if not user:
        raise UnauthorizedException("No active user found in system. Please provide X-User-Id header.")

    return user


async def require_manager_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Enforces that the current user has either MANAGER or ADMIN role."""
    if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise ForbiddenException(
            f"Access Denied: User '{current_user.username}' with role '{current_user.role.value}' is not authorized. Requires MANAGER or ADMIN."
        )
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
ManagerUserDep = Annotated[User, Depends(require_manager_or_admin)]
