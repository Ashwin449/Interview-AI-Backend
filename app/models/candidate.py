import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.auth import User


class CandidateProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="candidate_profile")  # noqa: F821
    resumes: Mapped[list["Resume"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    candidate_experience: Mapped[list["CandidateExperience"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class Resume(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["CandidateProfile"] = relationship(back_populates="resumes")
    analysis: Mapped["ResumeAnalysis | None"] = relationship(
        back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )


class ResumeAnalysis(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "resume_analysis"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), unique=True
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_experience: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analysis_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume: Mapped["Resume"] = relationship(back_populates="analysis")


class Skill(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CandidateSkill(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "candidate_skills"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"))
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # RESUME | SELF_REPORTED | INTERVIEW
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship(back_populates="candidate_skills")
    skill: Mapped["Skill"] = relationship()


class CandidateExperience(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "candidate_experience"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    candidate: Mapped["CandidateProfile"] = relationship(back_populates="candidate_experience")
