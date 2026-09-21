from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.auth import RefreshToken, Role, User, UserRole
from app.models.candidate import CandidateProfile
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("An account with this email already exists")

    role_result = await db.execute(select(Role).where(Role.name == payload.role))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Role '{payload.role}' is not configured. Seed roles first.")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
    )
    db.add(user)
    await db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))

    if payload.role == "USER":
        db.add(CandidateProfile(user_id=user.id))

    await db.commit()

    result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role)).where(User.id == user.id)
    )
    return result.scalar_one()


async def authenticate_and_issue_tokens(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role)).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")

    return await _issue_tokens(db, user)
 

async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked_at is not None or stored.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token is invalid or expired")

    stored.revoked_at = datetime.now(timezone.utc)

    user_result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role)).where(User.id == stored.user_id)
    )
    user = user_result.scalar_one()
    return await _issue_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    role_names = [ur.role.name for ur in user.user_roles]
    access_token = create_access_token(subject=str(user.id), roles=role_names)

    raw_refresh, refresh_hash = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_token_expiry(),
        )  
    )
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)
