from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.auth import User
from app.models.candidate import CandidateProfile
from app.schemas.candidate import CandidateProfileResponse, CandidateProfileUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me/profile", response_model=CandidateProfileResponse)
async def get_my_profile(
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    return result.scalar_one()


@router.patch("/me/profile", response_model=CandidateProfileResponse)
async def update_my_profile(
    payload: CandidateProfileUpdateRequest,
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one()

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile
