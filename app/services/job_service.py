import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.candidate import CandidateProfile, Skill
from app.models.job import Job, JobCandidate, JobSkill
from app.models.enums import JobCandidateStatus
from app.schemas.job import JobCreateRequest


async def create_job(db: AsyncSession, created_by: uuid.UUID, payload: JobCreateRequest) -> Job:
    job = Job(
        created_by=created_by,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        experience_min=payload.experience_min,
        experience_max=payload.experience_max,
    )
    db.add(job)
    await db.flush()

    for skill_input in payload.skills:
        skill_result = await db.execute(select(Skill).where(Skill.name.ilike(skill_input.skill_name)))
        skill = skill_result.scalar_one_or_none()
        if skill is None:
            skill = Skill(name=skill_input.skill_name)
            db.add(skill)
            await db.flush()

        db.add(
            JobSkill(
                job_id=job.id,
                skill_id=skill.id,
                is_required=skill_input.is_required,
                importance_weight=skill_input.importance_weight,
                minimum_proficiency=skill_input.minimum_proficiency,
            )
        )

    await db.commit()

    result = await db.execute(select(Job).options(selectinload(Job.job_skills)).where(Job.id == job.id))
    return result.scalar_one()


async def list_jobs(db: AsyncSession) -> list[Job]:
    result = await db.execute(select(Job).options(selectinload(Job.job_skills)).order_by(Job.created_at.desc()))
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job:
    result = await db.execute(select(Job).options(selectinload(Job.job_skills)).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found")
    return job


async def invite_candidate(db: AsyncSession, job_id: uuid.UUID, candidate_id: uuid.UUID) -> JobCandidate:
    job = await get_job(db, job_id)

    candidate_result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    if candidate_result.scalar_one_or_none() is None:
        raise NotFoundError("Candidate profile not found")

    invite = JobCandidate(
        job_id=job.id,
        candidate_id=candidate_id,
        status=JobCandidateStatus.INVITED,
        invited_at=datetime.now(timezone.utc),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite
