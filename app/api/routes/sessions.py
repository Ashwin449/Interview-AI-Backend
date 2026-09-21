import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.auth import User
from app.models.interview import InterviewBlueprint, InterviewQuestion
from app.schemas.interview import AnswerResponse, QuestionResponse, SessionStartResponse
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


async def _to_start_response(db: AsyncSession, session) -> SessionStartResponse:
    current_question = None
    if session.current_question_id:
        q_result = await db.execute(select(InterviewQuestion).where(InterviewQuestion.id == session.current_question_id))
        q = q_result.scalar_one_or_none()
        if q:
            current_question = QuestionResponse.model_validate(q)

    blueprint_result = await db.execute(
        select(InterviewBlueprint.total_questions).where(InterviewBlueprint.interview_id == session.interview_id)
    )
    blueprint_total = blueprint_result.scalar_one_or_none() or 0

    return SessionStartResponse(
        id=session.id,
        session_token=session.session_token,
        status=session.status,
        current_question_no=session.current_question_no,
        total_questions=blueprint_total,
        current_question=current_question,
    )


@router.post("/{interview_id}/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.start_session(db, interview_id)
    return await _to_start_response(db, session)


@router.get("/{session_token}", response_model=SessionStartResponse)
async def get_session(
    session_token: str,
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, session_token)
    return await _to_start_response(db, session)


@router.post("/{session_token}/answers/text", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def submit_text_answer(
    session_token: str,
    question_id: uuid.UUID = Form(...),
    answer_text: str = Form(...),
    duration_seconds: int | None = Form(None),
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    return await session_service.submit_text_answer(db, session_token, question_id, answer_text, duration_seconds)


@router.post("/{session_token}/answers/audio", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def submit_audio_answer(
    session_token: str,
    question_id: uuid.UUID = Form(...),
    duration_seconds: int | None = Form(None),
    audio: UploadFile = File(...),
    current_user: User = Depends(require_roles("USER")),
    db: AsyncSession = Depends(get_db),
):
    return await session_service.submit_audio_answer(db, session_token, question_id, audio, duration_seconds)
