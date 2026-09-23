import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    AnswerType,
    InterviewStatus,
    InterviewType,
    ProcessingStatus,
    QuestionType,
    SessionStatus,
)


class InterviewCreateRequest(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID | None = None
    title: str
    interview_type: InterviewType
    difficulty: str | None = "MEDIUM"
    duration_minutes: int = 30
    total_questions: int = 10
    scheduled_at: datetime | None = None  # NEW — powers "Upcoming Interviews" + the Date & Time column


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    candidate_id: uuid.UUID
    interviewer_id: uuid.UUID | None
    title: str
    interview_type: InterviewType
    difficulty: str | None
    duration_minutes: int
    scheduled_at: datetime | None  # NEW
    status: InterviewStatus
    started_at: datetime | None
    completed_at: datetime | None
    overall_score: float | None


class BlueprintCompetencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    weight: float
    question_count: int
    difficulty: str | None


class BlueprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    version: int
    status: str
    total_questions: int
    duration_minutes: int
    competencies: list[BlueprintCompetencyResponse] = []


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_number: int
    question_text: str
    question_type: QuestionType
    difficulty: str | None
    is_follow_up: bool
    parent_question_id: uuid.UUID | None


class SessionStartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_token: str
    status: SessionStatus
    current_question_no: int
    total_questions: int
    current_question: QuestionResponse | None = None


class SubmitTextAnswerRequest(BaseModel):
    question_id: uuid.UUID
    answer_text: str
    duration_seconds: int | None = None


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    answer_type: AnswerType
    transcription_status: ProcessingStatus
    evaluation_status: ProcessingStatus


class NextQuestionResponse(BaseModel):
    interview_complete: bool
    current_question_no: int
    total_questions: int
    question: QuestionResponse | None = None