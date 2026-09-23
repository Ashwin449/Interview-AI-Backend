from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.schemas.admin_views import DashboardSummaryResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user=Depends(require_roles("ADMIN", "INTERVIEWER")),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_summary(db)