import uuid
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.auth import User, UserRole

bearer_scheme = HTTPBearer(description="Paste the access_token returned by POST /api/auth/login")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Malformed subject claim") from exc

    result = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


def require_roles(*allowed_roles: str) -> Callable:
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_names = {ur.role.name for ur in current_user.user_roles}
        if not user_role_names.intersection(allowed_roles):
            raise ForbiddenError(f"Requires one of roles: {', '.join(allowed_roles)}")
        return current_user

    return _checker