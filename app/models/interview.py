import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AnswerType,
    BlueprintStatus,
    InterviewStatus,
    InterviewType,
    ProcessingStatus,
    QuestionType,
    SessionStatus,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation, CompetencyScore, InterviewReport


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interviews"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    interview_type: Mapped[InterviewType] = mapped_column(Enum(InterviewType, name="interview_type"))
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"), default=InterviewStatus.SCHEDULED
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    blueprint: Mapped["InterviewBlueprint | None"] = relationship(
        back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.question_number"
    )
    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    competency_scores: Mapped[list["CompetencyScore"]] = relationship(  # noqa: F821
        back_populates="interview", cascade="all, delete-orphan"
    )
    report: Mapped["InterviewReport | None"] = relationship(  # noqa: F821
        back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )


class InterviewBlueprint(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_blueprints"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), unique=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[BlueprintStatus] = mapped_column(
        Enum(BlueprintStatus, name="blueprint_status"), default=BlueprintStatus.DRAFT
    )
    total_questions: Mapped[int] = mapped_column(Integer, default=10)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    strategy_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    generated_by_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="blueprint")
    competencies: Mapped[list["BlueprintCompetency"]] = relationship(
        back_populates="blueprint", cascade="all, delete-orphan"
    )


class BlueprintCompetency(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "blueprint_competencies"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_blueprints.id", ondelete="CASCADE")
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    question_count: Mapped[int] = mapped_column(Integer, default=1)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    blueprint: Mapped["InterviewBlueprint"] = relationship(back_populates="competencies")
    rubric: Mapped["EvaluationRubric | None"] = relationship(
        back_populates="competency", uselist=False, cascade="all, delete-orphan"
    )
    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="competency")


class EvaluationRubric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "evaluation_rubrics"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_blueprints.id", ondelete="CASCADE")
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_competencies.id", ondelete="CASCADE"), unique=True
    )
    criteria_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competency: Mapped["BlueprintCompetency"] = relationship(back_populates="rubric")


class InterviewQuestion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_questions"

    interview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"))
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_competencies.id", ondelete="SET NULL"), nullable=True
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, name="question_type"))
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_concepts: Mapped[list[str]] = mapped_column(JSONB, default=list)
    evaluation_rubric: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="questions")
    competency: Mapped["BlueprintCompetency | None"] = relationship(back_populates="questions")
    follow_ups: Mapped[list["InterviewQuestion"]] = relationship(back_populates="parent_question")
    parent_question: Mapped["InterviewQuestion | None"] = relationship(
        back_populates="follow_ups", remote_side="InterviewQuestion.id"
    )
    answers: Mapped[list["CandidateAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class InterviewSession(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_sessions"

    interview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"))
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus, name="session_status"), default=SessionStatus.NOT_STARTED)
    current_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    current_question_no: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    interview: Mapped["Interview"] = relationship(back_populates="sessions")
    answers: Mapped[list["CandidateAnswer"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class CandidateAnswer(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "candidate_answers"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE")
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE")
    )
    answer_type: Mapped[AnswerType] = mapped_column(Enum(AnswerType, name="answer_type"), default=AnswerType.TEXT)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcription_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="transcription_status"), default=ProcessingStatus.PENDING
    )
    evaluation_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="answer_evaluation_status"), default=ProcessingStatus.PENDING
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="answers")
    question: Mapped["InterviewQuestion"] = relationship(back_populates="answers")
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )
    evaluation: Mapped["Evaluation | None"] = relationship(  # noqa: F821
        back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )


class Transcript(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "transcripts"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_answers.id", ondelete="CASCADE"), unique=True
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answer: Mapped["CandidateAnswer"] = relationship(back_populates="transcript")
