import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobCandidateStatus, JobStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile,Skill


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    experience_min: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    experience_max: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.DRAFT)

    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    job_candidates: Mapped[list["JobCandidate"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    importance_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    minimum_proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship()  

class JobCandidate(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_candidates"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    status: Mapped[JobCandidateStatus] = mapped_column(
        Enum(JobCandidateStatus, name="job_candidate_status"), default=JobCandidateStatus.INVITED
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="job_candidates")
    candidate: Mapped["CandidateProfile"] = relationship()  
 