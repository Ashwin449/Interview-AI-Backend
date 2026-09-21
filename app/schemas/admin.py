import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    old_values: dict
    new_values: dict
    created_at: datetime


class SystemSettingUpsertRequest(BaseModel):
    key: str
    value: str
    description: str | None = None


class SystemSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    value: str
    description: str | None
    updated_at: datetime


class AssignRoleRequest(BaseModel):
    user_id: uuid.UUID
    role: str
