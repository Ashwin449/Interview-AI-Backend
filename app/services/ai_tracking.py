import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIRun
from app.models.enums import AIOperation, AIRunStatus


async def record_ai_run(
    db: AsyncSession,
    operation: AIOperation,
    entity_type: str,
    entity_id: uuid.UUID | None,
    model_name: str,
    prompt_version: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any] | None,
    status: AIRunStatus,
    execution_time_ms: int | None,
    error_message: str | None = None,
) -> AIRun:
    run = AIRun(
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        model_name=model_name,
        prompt_version=prompt_version,
        input_data=input_data,
        output_data=output_data or {},
        status=status,
        execution_time_ms=execution_time_ms,
        error_message=error_message,
    )
    db.add(run)
    await db.flush()
    return run
