import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExtractedSkill(BaseModel):
    name: str
    level: str | None = None
    years: float | None = None


class ResumeAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    summary: str | None
    total_experience: float | None
    current_role: str | None
    analysis_json: dict
    model_name: str | None
    created_at: datetime


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_type: str
    file_size: int
    version: int
    is_current: bool
    uploaded_at: datetime
    analysis: ResumeAnalysisResponse | None = None


class CandidateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    headline: str | None
    location: str | None
    years_experience: float | None
    current_company: str | None
    current_role: str | None
    education_summary: str | None


class CandidateProfileUpdateRequest(BaseModel):
    headline: str | None = None
    location: str | None = None
    current_company: str | None = None
    current_role: str | None = None
    education_summary: str | None = None
