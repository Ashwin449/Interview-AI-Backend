import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import Recommendation

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.candidate import CandidateAnswer
    from app.models.interview import Interview
    from app.models.interview import BlueprintCompetency



class Evaluation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_answers.id", ondelete="CASCADE"), unique=True
    )

    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    reasoning_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    strengths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, default=list)
    missing_concepts: Mapped[list[str]] = mapped_column(JSONB, default=list)

    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    needs_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answer: Mapped["CandidateAnswer"] = relationship(back_populates="evaluation")  # noqa: F821


class CompetencyScore(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "competency_scores"

    interview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"))
    competency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_competencies.id", ondelete="CASCADE")
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_passed: Mapped[int] = mapped_column(Integer, default=0)
    strengths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="competency_scores")  # noqa: F821
    competency: Mapped["BlueprintCompetency"] = relationship()  # noqa: F821


class InterviewReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_reports"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), unique=True
    )
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    problem_solving: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommendation: Mapped[Recommendation | None] = mapped_column(
        Enum(Recommendation, name="recommendation"), nullable=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    generated_by_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="report")  # noqa: F821
