import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Recommendation


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    answer_id: uuid.UUID
    overall_score: float | None
    technical_score: float | None
    relevance_score: float | None
    completeness_score: float | None
    reasoning_score: float | None
    communication_score: float | None
    strengths: list[str]
    weaknesses: list[str]
    missing_concepts: list[str]
    feedback: str | None
    needs_follow_up: bool


class CompetencyScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency_id: uuid.UUID
    score: float
    questions_attempted: int
    questions_passed: int
    strengths: list[str]
    weaknesses: list[str]


class InterviewReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    overall_score: float | None
    technical_score: float | None
    problem_solving: float | None
    communication_score: float | None
    recommendation: Recommendation | None
    summary: str | None
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    created_at: datetime
    competency_scores: list[CompetencyScoreResponse] = []
