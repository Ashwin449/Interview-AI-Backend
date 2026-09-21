import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.auth import User
from app.models.candidate import CandidateProfile, Resume
from app.schemas.candidate import ResumeAnalysisResponse, ResumeResponse
from app.services import resume_service

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    resume = await resume_service.upload_resume(db, current_user.id, file)
    return resume


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    return await resume_service.analyze_and_apply_resume(db, resume_id)


@router.get("/me", response_model=list[ResumeResponse])
async def my_resumes(current_user: User = Depends(require_roles("USER")), db: AsyncSession = Depends(get_db)):
    profile_result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = profile_result.scalar_one()
    result = await db.execute(
        select(Resume)
        .options(selectinload(Resume.analysis))
        .where(Resume.candidate_id == profile.id)
        .order_by(Resume.version.desc())
    )
    return list(result.scalars().all())
