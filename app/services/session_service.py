import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.answer_evaluator import PROMPT_VERSION as EVAL_PROMPT_VERSION
from app.ai.answer_evaluator import evaluate_answer
from app.ai.question_generator import PROMPT_VERSION as FOLLOWUP_PROMPT_VERSION
from app.ai.question_generator import generate_follow_up_question
from app.ai.report_generator import PROMPT_VERSION as REPORT_PROMPT_VERSION
from app.ai.report_generator import generate_interview_report
from app.ai.whisper_client import whisper_client
from app.core.config import get_settings
from app.core.exceptions import AIServiceError, NotFoundError, ValidationFailedError
from app.models.enums import AIOperation, AIRunStatus, AnswerType, InterviewStatus, ProcessingStatus, SessionStatus
from app.models.evaluation import CompetencyScore, Evaluation, InterviewReport
from app.models.interview import (
    BlueprintCompetency,
    CandidateAnswer,
    Interview,
    InterviewBlueprint,
    InterviewQuestion,
    InterviewSession,
    Transcript,
)
from app.services.ai_tracking import record_ai_run

settings = get_settings()


async def _ordered_plan(db: AsyncSession, interview_id: uuid.UUID) -> list[InterviewQuestion]:
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.interview_id == interview_id, InterviewQuestion.is_follow_up.is_(False))
        .order_by(InterviewQuestion.question_number)
    )
    return list(result.scalars().all())


async def start_session(db: AsyncSession, interview_id: uuid.UUID) -> InterviewSession:
    interview_result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = interview_result.scalar_one_or_none()
    if interview is None:
        raise NotFoundError("Interview not found")

    plan = await _ordered_plan(db, interview_id)
    if not plan:
        raise ValidationFailedError("Generate interview questions before starting a session")

    now = datetime.now(timezone.utc)
    session = InterviewSession(
        interview_id=interview_id,
        session_token=secrets.token_urlsafe(32),
        status=SessionStatus.ACTIVE,
        current_question_id=plan[0].id,
        current_question_no=1,
        started_at=now,
        last_activity_at=now,
    )
    db.add(session)

    interview.status = InterviewStatus.IN_PROGRESS
    interview.started_at = interview.started_at or now

    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_token: str) -> InterviewSession:
    result = await db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.interview))
        .where(InterviewSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("Interview session not found")
    return session


async def submit_text_answer(
    db: AsyncSession, session_token: str, question_id: uuid.UUID, answer_text: str, duration_seconds: int | None
) -> CandidateAnswer:
    session = await get_session(db, session_token)
    _validate_active_question(session, question_id)

    now = datetime.now(timezone.utc)
    answer = CandidateAnswer(
        session_id=session.id,
        question_id=question_id,
        answer_type=AnswerType.TEXT,
        answer_text=answer_text,
        started_at=now,
        submitted_at=now,
        duration_seconds=duration_seconds,
        transcription_status=ProcessingStatus.COMPLETED,
        evaluation_status=ProcessingStatus.PENDING,
    )
    db.add(answer)
    session.last_activity_at = now
    await db.commit()
    await db.refresh(answer)

    await _evaluate_and_advance(db, session, answer)
    return answer


async def submit_audio_answer(
    db: AsyncSession, session_token: str, question_id: uuid.UUID, audio: UploadFile, duration_seconds: int | None
) -> CandidateAnswer:
    session = await get_session(db, session_token)
    _validate_active_question(session, question_id)

    storage_dir = Path(settings.audio_storage_dir) / "answers" / str(session.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_ext = Path(audio.filename or "answer.wav").suffix or ".wav"
    audio_path = storage_dir / f"{uuid.uuid4()}{file_ext}"
    audio_path.write_bytes(await audio.read())

    now = datetime.now(timezone.utc)
    answer = CandidateAnswer(
        session_id=session.id,
        question_id=question_id,
        answer_type=AnswerType.AUDIO,
        audio_path=str(audio_path),
        started_at=now,
        submitted_at=now,
        duration_seconds=duration_seconds,
        transcription_status=ProcessingStatus.PROCESSING,
        evaluation_status=ProcessingStatus.PENDING,
    )
    db.add(answer)
    session.last_activity_at = now
    await db.commit()
    await db.refresh(answer)

    try:
        text, language, confidence, elapsed_ms = whisper_client.transcribe(str(audio_path))
    except AIServiceError:
        answer.transcription_status = ProcessingStatus.FAILED
        await db.commit()
        raise

    db.add(
        Transcript(
            answer_id=answer.id,
            transcript_text=text,
            language=language,
            confidence_score=confidence,
            model_name=f"faster-whisper-{settings.whisper_model_size}",
            processing_time_ms=elapsed_ms,
        )
    )
    answer.answer_text = text
    answer.transcription_status = ProcessingStatus.COMPLETED
    await db.commit()
    await db.refresh(answer)

    await _evaluate_and_advance(db, session, answer)
    return answer


def _validate_active_question(session: InterviewSession, question_id: uuid.UUID) -> None:
    if session.status != SessionStatus.ACTIVE:
        raise ValidationFailedError("Interview session is not active")
    if session.current_question_id != question_id:
        raise ValidationFailedError("This is not the current question for this session")


async def _evaluate_and_advance(db: AsyncSession, session: InterviewSession, answer: CandidateAnswer) -> None:
    question_result = await db.execute(select(InterviewQuestion).where(InterviewQuestion.id == answer.question_id))
    question = question_result.scalar_one()

    parsed, elapsed_ms = await evaluate_answer(
        question_text=question.question_text,
        expected_concepts=question.expected_concepts,
        answer_text=answer.answer_text or "",
    )

    await record_ai_run(
        db,
        operation=AIOperation.ANSWER_EVALUATION,
        entity_type="candidate_answer",
        entity_id=answer.id,
        model_name="ollama",
        prompt_version=EVAL_PROMPT_VERSION,
        input_data={"question_id": str(question.id)},
        output_data=parsed,
        status=AIRunStatus.SUCCEEDED,
        execution_time_ms=elapsed_ms,
    )

    evaluation = Evaluation(
        answer_id=answer.id,
        overall_score=parsed.get("overall_score"),
        technical_score=parsed.get("technical_score"),
        relevance_score=parsed.get("relevance_score"),
        completeness_score=parsed.get("completeness_score"),
        reasoning_score=parsed.get("reasoning_score"),
        communication_score=parsed.get("communication_score"),
        strengths=parsed.get("strengths", []),
        weaknesses=parsed.get("weaknesses", []),
        missing_concepts=parsed.get("missing_concepts", []),
        feedback=parsed.get("feedback"),
        needs_follow_up=bool(parsed.get("needs_follow_up", False)),
        follow_up_reason=parsed.get("follow_up_reason"),
        model_name="ollama",
        prompt_version=EVAL_PROMPT_VERSION,
    )
    db.add(evaluation)
    answer.evaluation_status = ProcessingStatus.COMPLETED
    await db.flush()

    can_follow_up = not question.is_follow_up  # cap adaptive branching to one level
    if evaluation.needs_follow_up and can_follow_up:
        await _generate_and_queue_follow_up(db, session, question, answer, evaluation)
    else:
        await _advance_past(db, session, question)

    await db.commit()


async def _generate_and_queue_follow_up(
    db: AsyncSession,
    session: InterviewSession,
    question: InterviewQuestion,
    answer: CandidateAnswer,
    evaluation: Evaluation,
) -> None:
    parsed, elapsed_ms = await generate_follow_up_question(
        original_question=question.question_text,
        candidate_answer=answer.answer_text or "",
        missing_concepts=evaluation.missing_concepts,
    )

    await record_ai_run(
        db,
        operation=AIOperation.FOLLOW_UP_GENERATION,
        entity_type="interview_question",
        entity_id=question.id,
        model_name="ollama",
        prompt_version=FOLLOWUP_PROMPT_VERSION,
        input_data={"parent_question_id": str(question.id)},
        output_data=parsed,
        status=AIRunStatus.SUCCEEDED,
        execution_time_ms=elapsed_ms,
    )

    max_number_result = await db.execute(
        select(func.max(InterviewQuestion.question_number)).where(
            InterviewQuestion.interview_id == session.interview_id
        )
    )
    next_number = (max_number_result.scalar() or 0) + 1

    follow_up = InterviewQuestion(
        interview_id=session.interview_id,
        competency_id=question.competency_id,
        question_number=next_number,
        question_text=parsed.get("question_text", ""),
        question_type="FOLLOW_UP",
        difficulty=parsed.get("difficulty"),
        expected_concepts=parsed.get("expected_concepts", []),
        is_ai_generated=True,
        is_follow_up=True,
        parent_question_id=question.id,
    )
    db.add(follow_up)
    await db.flush()

    session.current_question_id = follow_up.id
    session.current_question_no += 1


async def _advance_past(db: AsyncSession, session: InterviewSession, answered_question: InterviewQuestion) -> None:
    anchor_id = answered_question.parent_question_id if answered_question.is_follow_up else answered_question.id
    plan = await _ordered_plan(db, session.interview_id)
    plan_ids = [q.id for q in plan]

    try:
        idx = plan_ids.index(anchor_id)
    except ValueError:
        idx = len(plan_ids) - 1  # defensive fallback

    if idx + 1 < len(plan):
        next_question = plan[idx + 1]
        session.current_question_id = next_question.id
        session.current_question_no += 1
    else:
        await _complete_session(db, session)


async def _complete_session(db: AsyncSession, session: InterviewSession) -> None:
    now = datetime.now(timezone.utc)
    session.status = SessionStatus.COMPLETED
    session.current_question_id = None
    session.ended_at = now

    interview_result = await db.execute(select(Interview).where(Interview.id == session.interview_id))
    interview = interview_result.scalar_one()
    interview.status = InterviewStatus.COMPLETED
    interview.completed_at = now
    await db.flush()

    await _compute_scores_and_report(db, interview.id)


async def _compute_scores_and_report(db: AsyncSession, interview_id: uuid.UUID) -> InterviewReport:
    blueprint_result = await db.execute(
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.competencies))
        .where(InterviewBlueprint.interview_id == interview_id)
    )
    blueprint = blueprint_result.scalar_one()

    competency_score_rows: list[dict] = []
    all_evaluations: list[dict] = []

    for competency in blueprint.competencies:
        eval_result = await db.execute(
            select(Evaluation)
            .join(CandidateAnswer, CandidateAnswer.id == Evaluation.answer_id)
            .join(InterviewQuestion, InterviewQuestion.id == CandidateAnswer.question_id)
            .where(InterviewQuestion.competency_id == competency.id)
        )
        evaluations = list(eval_result.scalars().all())
        if not evaluations:
            continue

        avg_overall = sum(float(e.overall_score or 0) for e in evaluations) / len(evaluations)
        passed = sum(1 for e in evaluations if float(e.overall_score or 0) >= 6.0)
        strengths = sorted({s for e in evaluations for s in (e.strengths or [])})[:5]
        weaknesses = sorted({w for e in evaluations for w in (e.weaknesses or [])})[:5]

        score_pct = round(avg_overall * 10, 2)  # 0-10 -> 0-100 scale
        db.add(
            CompetencyScore(
                interview_id=interview_id,
                competency_id=competency.id,
                score=score_pct,
                questions_attempted=len(evaluations),
                questions_passed=passed,
                strengths=strengths,
                weaknesses=weaknesses,
            )
        )
        competency_score_rows.append({"name": competency.name, "score": score_pct, "weight": float(competency.weight)})
        all_evaluations.extend(
            {
                "overall_score": float(e.overall_score or 0),
                "technical_score": float(e.technical_score or 0),
                "communication_score": float(e.communication_score or 0),
                "weaknesses": e.weaknesses,
                "missing_concepts": e.missing_concepts,
            }
            for e in evaluations
        )

    parsed, elapsed_ms = await generate_interview_report(competency_score_rows, all_evaluations)

    await record_ai_run(
        db,
        operation=AIOperation.REPORT_GENERATION,
        entity_type="interview",
        entity_id=interview_id,
        model_name="ollama",
        prompt_version=REPORT_PROMPT_VERSION,
        input_data={"competency_scores": competency_score_rows},
        output_data=parsed,
        status=AIRunStatus.SUCCEEDED,
        execution_time_ms=elapsed_ms,
    )

    overall_score_pct = round(float(parsed.get("overall_score", 0)) * 10, 2)
    report = InterviewReport(
        interview_id=interview_id,
        overall_score=overall_score_pct,
        technical_score=round(float(parsed.get("technical_score", 0)) * 10, 2),
        problem_solving=round(float(parsed.get("problem_solving", 0)) * 10, 2),
        communication_score=round(float(parsed.get("communication_score", 0)) * 10, 2),
        recommendation=parsed.get("recommendation"),
        summary=parsed.get("summary"),
        strengths=parsed.get("strengths", []),
        weaknesses=parsed.get("weaknesses", []),
        recommendations=parsed.get("recommendations", []),
        generated_by_model="ollama",
    )
    db.add(report)

    interview_result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = interview_result.scalar_one()
    interview.overall_score = overall_score_pct

    await db.commit()
    await db.refresh(report)
    return report


async def get_report(db: AsyncSession, interview_id: uuid.UUID) -> InterviewReport:
    result = await db.execute(
        select(InterviewReport)
        .options(selectinload(InterviewReport.interview))
        .where(InterviewReport.interview_id == interview_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report not available yet — interview may not be complete")
    return report


async def get_competency_scores(db: AsyncSession, interview_id: uuid.UUID) -> list[CompetencyScore]:
    result = await db.execute(select(CompetencyScore).where(CompetencyScore.interview_id == interview_id))
    return list(result.scalars().all())
