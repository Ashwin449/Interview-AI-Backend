import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.auth import User
from app.models.enums import InterviewStatus
from app.schemas.admin_views import InterviewListResponse
from app.schemas.evaluation import CompetencyScoreResponse, InterviewReportResponse
from app.schemas.interview import BlueprintResponse, InterviewCreateRequest, InterviewResponse, QuestionResponse
from app.services import interview_service, session_service

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


@router.get("", response_model=InterviewListResponse)
async def list_interviews(
    status_filter: InterviewStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await interview_service.list_interviews(
        db, status_filter=status_filter, search=search, skip=skip, limit=limit
    )
    return InterviewListResponse(items=items, total=total)


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreateRequest,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await interview_service.create_interview(db, current_user.id, payload)


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN", "USER")),
    db: AsyncSession = Depends(get_db),
):
    return await interview_service.get_interview(db, interview_id)


@router.post("/{interview_id}/blueprint", response_model=BlueprintResponse, status_code=status.HTTP_201_CREATED)
async def generate_blueprint(
    interview_id: uuid.UUID,
    total_questions: int = 10,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await interview_service.generate_interview_blueprint(db, interview_id, total_questions)


@router.post("/{interview_id}/questions", response_model=list[QuestionResponse], status_code=status.HTTP_201_CREATED)
async def generate_questions(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await interview_service.generate_interview_questions(db, interview_id)


@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
async def get_report(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles("INTERVIEWER", "ADMIN", "USER")),
    db: AsyncSession = Depends(get_db),
):
    report = await session_service.get_report(db, interview_id)
    competency_scores = await session_service.get_competency_scores(db, interview_id)
    return InterviewReportResponse(
        id=report.id,
        interview_id=report.interview_id,
        overall_score=report.overall_score,
        technical_score=report.technical_score,
        problem_solving=report.problem_solving,
        communication_score=report.communication_score,
        recommendation=report.recommendation,
        summary=report.summary,
        strengths=report.strengths,
        weaknesses=report.weaknesses,
        recommendations=report.recommendations,
        created_at=report.created_at,
        competency_scores=[
            CompetencyScoreResponse(
                competency_id=cs.competency_id,
                score=cs.score,
                questions_attempted=cs.questions_attempted,
                questions_passed=cs.questions_passed,
                strengths=cs.strengths,
                weaknesses=cs.weaknesses,
            )
            for cs in competency_scores
        ],
    )