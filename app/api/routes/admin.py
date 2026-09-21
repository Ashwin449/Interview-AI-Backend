import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.auth import User
from app.schemas.admin import (
    AssignRoleRequest,
    AuditLogResponse,
    SystemSettingResponse,
    SystemSettingUpsertRequest,
)
from app.schemas.auth import UserResponse
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_roles("ADMIN"))])


@router.get("/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await admin_service.list_users(db)
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            phone=u.phone,
            is_active=u.is_active,
            is_verified=u.is_verified,
            roles=u.role_names,
        )
        for u in users
    ]


@router.patch("/users/{user_id}/active", response_model=UserResponse)
async def set_user_active(
    user_id: uuid.UUID,
    is_active: bool,
    current_user: User = Depends(require_roles("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.set_user_active(db, user_id, is_active)
    await admin_service.log_action(
        db,
        user_id=current_user.id,
        action="SET_USER_ACTIVE",
        entity_type="user",
        entity_id=user_id,
        new_values={"is_active": is_active},
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=user.role_names,
    )


@router.post("/roles/assign", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role(
    payload: AssignRoleRequest,
    current_user: User = Depends(require_roles("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.assign_role(db, payload.user_id, payload.role)
    await admin_service.log_action(
        db,
        user_id=current_user.id,
        action="ASSIGN_ROLE",
        entity_type="user",
        entity_id=payload.user_id,
        new_values={"role": payload.role},
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await admin_service.list_audit_logs(db, limit)


@router.put("/settings", response_model=SystemSettingResponse)
async def upsert_setting(
    payload: SystemSettingUpsertRequest,
    current_user: User = Depends(require_roles("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.upsert_system_setting(
        db, payload.key, payload.value, payload.description, current_user.id
    )


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_settings(db: AsyncSession = Depends(get_db)):
    return await admin_service.list_system_settings(db)
