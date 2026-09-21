import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.resume_analyzer import PROMPT_VERSION, analyze_resume_text
from app.core.config import get_settings
from app.core.exceptions import AIServiceError, NotFoundError
from app.models.candidate import CandidateExperience, CandidateProfile, CandidateSkill, Resume, ResumeAnalysis, Skill
from app.models.enums import AIOperation, AIRunStatus
from app.services.ai_tracking import record_ai_run

settings = get_settings()


def _extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


async def _get_candidate_profile(db: AsyncSession, user_id: uuid.UUID) -> CandidateProfile:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Candidate profile not found for this user")
    return profile


async def upload_resume(db: AsyncSession, user_id: uuid.UUID, upload: UploadFile) -> Resume:
    profile = await _get_candidate_profile(db, user_id)

    storage_dir = Path(settings.resume_storage_dir) / str(profile.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = await upload.read()
    file_ext = Path(upload.filename or "resume.pdf").suffix or ".pdf"
    stored_name = f"{uuid.uuid4()}{file_ext}"
    stored_path = storage_dir / stored_name
    stored_path.write_bytes(file_bytes)

    # Mark previous resumes as not-current and bump version.
    prev_result = await db.execute(
        select(Resume).where(Resume.candidate_id == profile.id).order_by(Resume.version.desc())
    )
    prev_resumes = prev_result.scalars().all()
    next_version = (prev_resumes[0].version + 1) if prev_resumes else 1
    if prev_resumes:
        await db.execute(
            update(Resume).where(Resume.candidate_id == profile.id).values(is_current=False)
        )

    resume = Resume(
        candidate_id=profile.id,
        file_name=upload.filename or stored_name,
        file_path=str(stored_path),
        file_type=upload.content_type or "application/octet-stream",
        file_size=len(file_bytes),
        version=next_version,
        is_current=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


async def analyze_and_apply_resume(db: AsyncSession, resume_id: uuid.UUID) -> ResumeAnalysis:
    result = await db.execute(
        select(Resume).options(selectinload(Resume.candidate)).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise NotFoundError("Resume not found")

    try:
        raw_text = _extract_pdf_text(resume.file_path) if resume.file_type == "application/pdf" else Path(
            resume.file_path
        ).read_text(errors="ignore")
    except Exception as exc:  # noqa: BLE001
        raise AIServiceError(f"Could not extract text from resume file: {exc}") from exc

    status = AIRunStatus.SUCCEEDED
    error_message = None
    try:
        parsed, elapsed_ms = await analyze_resume_text(raw_text)
    except AIServiceError as exc:
        status = AIRunStatus.FAILED
        error_message = str(exc)
        await record_ai_run(
            db,
            operation=AIOperation.RESUME_ANALYSIS,
            entity_type="resume",
            entity_id=resume.id,
            model_name="ollama",
            prompt_version=PROMPT_VERSION,
            input_data={"resume_id": str(resume.id)},
            output_data=None,
            status=status,
            execution_time_ms=None,
            error_message=error_message,
        )
        await db.commit()
        raise

    await record_ai_run(
        db,
        operation=AIOperation.RESUME_ANALYSIS,
        entity_type="resume",
        entity_id=resume.id,
        model_name="ollama",
        prompt_version=PROMPT_VERSION,
        input_data={"resume_id": str(resume.id)},
        output_data=parsed,
        status=status,
        execution_time_ms=elapsed_ms,
    )

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        raw_text=raw_text[:50000],
        summary=parsed.get("summary"),
        total_experience=parsed.get("total_experience_years"),
        current_role=parsed.get("current_role"),
        analysis_json=parsed,
        model_name="ollama",
        prompt_version=PROMPT_VERSION,
    )
    db.add(analysis)

    # Fold extracted skills into candidate_skills (create Skill rows as needed).
    for skill_entry in parsed.get("skills", []):
        skill_name = skill_entry.get("name")
        if not skill_name:
            continue
        skill_result = await db.execute(select(Skill).where(Skill.name.ilike(skill_name)))
        skill = skill_result.scalar_one_or_none()
        if skill is None:
            skill = Skill(name=skill_name)
            db.add(skill)
            await db.flush()

        existing_cs = await db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_id == resume.candidate_id, CandidateSkill.skill_id == skill.id
            )
        )
        candidate_skill = existing_cs.scalar_one_or_none()
        if candidate_skill is None:
            db.add(
                CandidateSkill(
                    candidate_id=resume.candidate_id,
                    skill_id=skill.id,
                    proficiency=skill_entry.get("level"),
                    years_experience=skill_entry.get("years"),
                    source="RESUME",
                    confidence_score=0.8,
                )
            )
        else:
            candidate_skill.proficiency = skill_entry.get("level") or candidate_skill.proficiency
            candidate_skill.years_experience = skill_entry.get("years") or candidate_skill.years_experience

    # Fold extracted experience entries into candidate_experience.
    for exp in parsed.get("experience", []):
        db.add(
            CandidateExperience(
                candidate_id=resume.candidate_id,
                company_name=exp.get("company_name", "Unknown"),
                job_title=exp.get("job_title", "Unknown"),
                start_date=_parse_date(exp.get("start_date")),
                end_date=_parse_date(exp.get("end_date")),
                description=exp.get("description"),
                is_current=bool(exp.get("is_current", False)),
            )
        )

    await db.commit()
    await db.refresh(analysis)
    return analysis


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
