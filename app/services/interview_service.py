import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.blueprint_generator import PROMPT_VERSION as BLUEPRINT_PROMPT_VERSION
from app.ai.blueprint_generator import generate_blueprint
from app.ai.question_generator import PROMPT_VERSION as QUESTION_PROMPT_VERSION
from app.ai.question_generator import generate_questions_for_competency
from app.core.exceptions import NotFoundError
from app.models.candidate import CandidateProfile, ResumeAnalysis
from app.models.enums import AIOperation, AIRunStatus, BlueprintStatus
from app.models.interview import (
    BlueprintCompetency,
    EvaluationRubric,
    Interview,
    InterviewBlueprint,
    InterviewQuestion,
)
from app.models.job import Job, JobSkill
from app.models.candidate import Resume, Skill
from app.schemas.interview import InterviewCreateRequest
from app.services.ai_tracking import record_ai_run


async def create_interview(db: AsyncSession, interviewer_id: uuid.UUID | None, payload: InterviewCreateRequest) -> Interview:
    candidate_result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == payload.candidate_id))
    if candidate_result.scalar_one_or_none() is None:
        raise NotFoundError("Candidate profile not found")

    interview = Interview(
        job_id=payload.job_id,
        candidate_id=payload.candidate_id,
        interviewer_id=interviewer_id,
        title=payload.title,
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return interview


async def get_interview(db: AsyncSession, interview_id: uuid.UUID) -> Interview:
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if interview is None:
        raise NotFoundError("Interview not found")
    return interview


async def _latest_resume_summary(db: AsyncSession, candidate_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(ResumeAnalysis)
        .join(Resume, Resume.id == ResumeAnalysis.resume_id)
        .where(Resume.candidate_id == candidate_id, Resume.is_current.is_(True))
    )
    analysis = result.scalar_one_or_none()
    return analysis.summary if analysis else None


async def _job_skill_weights(db: AsyncSession, job_id: uuid.UUID | None) -> list[dict]:
    if job_id is None:
        return []
    result = await db.execute(
        select(JobSkill, Skill.name).join(Skill, Skill.id == JobSkill.skill_id).where(JobSkill.job_id == job_id)
    )
    return [{"name": name, "weight": float(js.importance_weight)} for js, name in result.all()]


async def generate_interview_blueprint(
    db: AsyncSession, interview_id: uuid.UUID, total_questions: int = 10
) -> InterviewBlueprint:
    interview = await get_interview(db, interview_id)

    existing = await db.execute(select(InterviewBlueprint).where(InterviewBlueprint.interview_id == interview.id))
    if existing.scalar_one_or_none() is not None:
        raise NotFoundError("Blueprint already exists for this interview")

    resume_summary = await _latest_resume_summary(db, interview.candidate_id)
    job_skills = await _job_skill_weights(db, interview.job_id)

    blueprint = InterviewBlueprint(
        interview_id=interview.id,
        status=BlueprintStatus.GENERATING,
        total_questions=total_questions,
        duration_minutes=interview.duration_minutes,
    )
    db.add(blueprint)
    await db.flush()

    parsed, elapsed_ms = await generate_blueprint(
        job_skills=job_skills,
        resume_summary=resume_summary,
        interview_type=interview.interview_type.value,
        difficulty=interview.difficulty,
        total_questions=total_questions,
    )

    await record_ai_run(
        db,
        operation=AIOperation.BLUEPRINT_GENERATION,
        entity_type="interview",
        entity_id=interview.id,
        model_name="ollama",
        prompt_version=BLUEPRINT_PROMPT_VERSION,
        input_data={"job_skills": job_skills, "total_questions": total_questions},
        output_data=parsed,
        status=AIRunStatus.SUCCEEDED,
        execution_time_ms=elapsed_ms,
    )

    blueprint.strategy_json = parsed
    blueprint.generated_by_model = "ollama"
    blueprint.prompt_version = BLUEPRINT_PROMPT_VERSION
    blueprint.status = BlueprintStatus.READY

    for idx, comp in enumerate(parsed.get("competencies", []), start=1):
        skill_result = await db.execute(select(Skill).where(Skill.name.ilike(comp.get("name", ""))))
        skill = skill_result.scalar_one_or_none()

        competency = BlueprintCompetency(
            blueprint_id=blueprint.id,
            skill_id=skill.id if skill else None,
            name=comp.get("name", f"Competency {idx}"),
            description=comp.get("description"),
            weight=comp.get("weight", 0),
            question_count=comp.get("question_count", 1),
            difficulty=comp.get("difficulty"),
            priority=comp.get("priority", idx),
        )
        db.add(competency)
        await db.flush()

        db.add(
            EvaluationRubric(
                blueprint_id=blueprint.id,
                competency_id=competency.id,
                criteria_json={"criteria": comp.get("rubric_criteria", [])},
            )
        )

    await db.commit()

    result = await db.execute(
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.competencies))
        .where(InterviewBlueprint.id == blueprint.id)
    )
    return result.scalar_one()


async def generate_interview_questions(db: AsyncSession, interview_id: uuid.UUID) -> list[InterviewQuestion]:
    interview = await get_interview(db, interview_id)

    blueprint_result = await db.execute(
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.competencies))
        .where(InterviewBlueprint.interview_id == interview.id)
    )
    blueprint = blueprint_result.scalar_one_or_none()
    if blueprint is None or blueprint.status != BlueprintStatus.READY:
        raise NotFoundError("A ready blueprint is required before generating questions")

    existing = await db.execute(select(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id))
    if existing.scalars().first() is not None:
        raise NotFoundError("Questions already generated for this interview")

    question_number = 1
    created_questions: list[InterviewQuestion] = []

    for competency in sorted(blueprint.competencies, key=lambda c: c.priority):
        parsed, elapsed_ms = await generate_questions_for_competency(
            competency_name=competency.name,
            competency_description=competency.description,
            difficulty=competency.difficulty,
            count=competency.question_count,
        )

        await record_ai_run(
            db,
            operation=AIOperation.QUESTION_GENERATION,
            entity_type="blueprint_competency",
            entity_id=competency.id,
            model_name="ollama",
            prompt_version=QUESTION_PROMPT_VERSION,
            input_data={"competency": competency.name, "count": competency.question_count},
            output_data=parsed,
            status=AIRunStatus.SUCCEEDED,
            execution_time_ms=elapsed_ms,
        )

        for q in parsed.get("questions", []):
            question = InterviewQuestion(
                interview_id=interview.id,
                competency_id=competency.id,
                question_number=question_number,
                question_text=q.get("question_text", ""),
                question_type=q.get("question_type", "TECHNICAL"),
                difficulty=q.get("difficulty"),
                expected_concepts=q.get("expected_concepts", []),
                is_ai_generated=True,
                is_follow_up=False,
            )
            db.add(question)
            created_questions.append(question)
            question_number += 1

    await db.commit()
    for q in created_questions:
        await db.refresh(q)
    return created_questions
