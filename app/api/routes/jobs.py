import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.auth import User
from app.schemas.job import JobCandidateInviteRequest, JobCandidateResponse, JobCreateRequest, JobResponse
from app.services import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.create_job(db, current_user.id, payload)


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN", "USER")),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.list_jobs(db)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN", "USER")),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.get_job(db, job_id)


@router.post("/{job_id}/invite", response_model=JobCandidateResponse, status_code=status.HTTP_201_CREATED)
async def invite_candidate(
    job_id: uuid.UUID,
    payload: JobCandidateInviteRequest,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.invite_candidate(db, job_id, payload.candidate_id)
