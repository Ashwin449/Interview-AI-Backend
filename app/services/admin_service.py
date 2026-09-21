import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import ConflictError, NotFoundError
from app.models.admin import AuditLog, SystemSetting
from app.models.auth import Role, User, UserRole


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role)).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def set_user_active(db: AsyncSession, user_id: uuid.UUID, is_active: bool) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user


async def assign_role(db: AsyncSession, user_id: uuid.UUID, role_name: str) -> None:
    user_result = await db.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise NotFoundError("User not found")

    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Role '{role_name}' not found")

    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("User already has this role")

    db.add(UserRole(user_id=user_id, role_id=role.id))
    await db.commit()


async def log_action(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_audit_logs(db: AsyncSession, limit: int = 100) -> list[AuditLog]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def upsert_system_setting(db: AsyncSession, key: str, value: str, description: str | None, updated_by: uuid.UUID) -> SystemSetting:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SystemSetting(key=key, value=value, description=description, updated_by=updated_by)
        db.add(setting)
    else:
        setting.value = value
        setting.description = description or setting.description
        setting.updated_by = updated_by
    await db.commit()
    await db.refresh(setting)
    return setting


async def list_system_settings(db: AsyncSession) -> list[SystemSetting]:
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return list(result.scalars().all())
