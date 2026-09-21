import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobCandidateStatus, JobStatus


class JobSkillInput(BaseModel):
    skill_name: str
    is_required: bool = True
    importance_weight: float = 0
    minimum_proficiency: str | None = None


class JobCreateRequest(BaseModel):
    title: str
    description: str | None = None
    department: str | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    skills: list[JobSkillInput] = []


class JobSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: uuid.UUID
    is_required: bool
    importance_weight: float
    minimum_proficiency: str | None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    department: str | None
    experience_min: float | None
    experience_max: float | None
    status: JobStatus
    job_skills: list[JobSkillResponse] = []


class JobCandidateInviteRequest(BaseModel):
    candidate_id: uuid.UUID


class JobCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: JobCandidateStatus
