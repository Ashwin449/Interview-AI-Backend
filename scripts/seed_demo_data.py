"""
Run once, after `python -m scripts.seed_roles` and `python -m scripts.seed_admin`,
to populate demo data so the admin dashboard / interviews list / resumes list
have something real to render instead of empty tables.

    python -m scripts.seed_admin      (must exist already - used as interviewer/creator)
    python -m scripts.seed_demo_data

Creates:
  - 9 candidate users (role USER) + their CandidateProfile rows
  - 5 jobs (Angular/Python/Full Stack/Data/Backend Developer)
  - 5 interviews across every status (SCHEDULED, IN_PROGRESS, COMPLETED x2, CANCELLED),
    with scheduled_at set relative to "now" so upcoming/recent actually populate
    however far in the future you run this
  - 4 resumes, 3 "Analyzed" (with a ResumeAnalysis row) and 1 "Processing" (without)

Safe to re-run: skips anything that already exists by email / title / file_name.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.auth import Role, User, UserRole
from app.models.candidate import CandidateProfile, Resume, ResumeAnalysis
from app.models.enums import InterviewStatus, InterviewType, JobStatus
from app.models.interview import Interview
from app.models.job import Job

DEMO_PASSWORD = "Candidate123!"  # every seeded candidate gets this password

CANDIDATES = [
    # (email, first_name, last_name, phone)
    ("john.doe@example.com", "John", "Doe", "+91 90000 00001"),
    ("sarah.smith@example.com", "Sarah", "Smith", "+91 90000 00002"),
    ("rahul.kumar@example.com", "Rahul", "Kumar", "+91 90000 00003"),
    ("anjali.patel@example.com", "Anjali", "Patel", "+91 90000 00004"),
    ("michael.scott@example.com", "Michael", "Scott", "+91 90000 00005"),
    ("rahul.sharma@example.com", "Rahul", "Sharma", "+91 90000 00006"),
    ("priya.mehta@example.com", "Priya", "Mehta", "+91 90000 00007"),
    ("amit.verma@example.com", "Amit", "Verma", "+91 90000 00008"),
    ("sneha.kapoor@example.com", "Sneha", "Kapoor", "+91 90000 00009"),
]

JOBS = [
    # (title, department, description)
    ("Angular Developer", "Engineering", "Front-end role building our Angular admin panel and candidate portal."),
    ("Python Developer", "Engineering", "Backend role on the FastAPI services powering interview generation."),
    ("Full Stack Developer", "Engineering", "End-to-end feature ownership across Angular + FastAPI."),
    ("Data Analyst", "Analytics", "Reporting and insights on interview outcomes and hiring funnels."),
    ("Backend Developer", "Engineering", "Core services, database design, and API reliability."),
]

NOW = datetime.now(timezone.utc)


def _at(days_offset: int, hour: int, minute: int = 0) -> datetime:
    base = NOW + timedelta(days=days_offset)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


# (candidate_email, job_title, title, interview_type, status, scheduled_at,
#  started_at, completed_at, overall_score)
INTERVIEWS = [
    (
        "john.doe@example.com", "Angular Developer", "Angular Developer - Technical Round",
        InterviewType.TECHNICAL, InterviewStatus.SCHEDULED,
        _at(1, 10, 30), None, None, None,
    ),
    (
        "sarah.smith@example.com", "Python Developer", "Python Developer - Technical Round",
        InterviewType.TECHNICAL, InterviewStatus.IN_PROGRESS,
        _at(0, 14, 0), NOW - timedelta(minutes=20), None, None,
    ),
    (
        "rahul.kumar@example.com", "Full Stack Developer", "Full Stack Developer - Technical Round",
        InterviewType.TECHNICAL, InterviewStatus.COMPLETED,
        _at(-2, 11, 0), _at(-2, 11, 0), _at(-2, 11, 45), 85.0,
    ),
    (
        "anjali.patel@example.com", "Data Analyst", "Data Analyst - Technical Round",
        InterviewType.TECHNICAL, InterviewStatus.COMPLETED,
        _at(-3, 15, 30), _at(-3, 15, 30), _at(-3, 16, 10), 92.0,
    ),
    (
        "michael.scott@example.com", "Backend Developer", "Backend Developer - Technical Round",
        InterviewType.TECHNICAL, InterviewStatus.CANCELLED,
        _at(-4, 13, 0), None, None, None,
    ),
]

# (candidate_email, file_name, file_type, uploaded_at, analyzed, summary)
RESUMES = [
    (
        "rahul.sharma@example.com", "rahul_sharma.pdf", "application/pdf",
        NOW - timedelta(days=1), True,
        "5 years of full-stack experience with Angular, FastAPI, and PostgreSQL.",
    ),
    (
        "priya.mehta@example.com", "priya_mehta.docx", "docx",
        NOW - timedelta(days=2), True,
        "3 years as a Python backend developer, strong in async APIs and testing.",
    ),
    (
        "amit.verma@example.com", "amit_verma.pdf", "application/pdf",
        NOW - timedelta(days=3), False, None,
    ),
    (
        "sneha.kapoor@example.com", "sneha_kapoor.pdf", "application/pdf",
        NOW - timedelta(days=4), True,
        "4 years in data analytics, SQL, and dashboarding with a focus on hiring metrics.",
    ),
]


async def _get_or_create_candidate(db, email, first_name, last_name, phone, user_role: Role) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=user_role.id))
    db.add(CandidateProfile(user_id=user.id))
    print(f"Created candidate '{email}'.")
    return user


async def _get_or_create_job(db, title, department, description, created_by) -> Job:
    result = await db.execute(select(Job).where(Job.title == title))
    job = result.scalar_one_or_none()
    if job is not None:
        return job

    job = Job(
        created_by=created_by,
        title=title,
        description=description,
        department=department,
        status=JobStatus.OPEN,
    )
    db.add(job)
    await db.flush()
    print(f"Created job '{title}'.")
    return job


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as db:
        admin_result = await db.execute(
            select(User).join(UserRole).join(Role).where(Role.name == "ADMIN")
        )
        admin = admin_result.scalars().first()
        if admin is None:
            raise SystemExit(
                "No ADMIN user found. Run `python -m scripts.seed_roles` then "
                "`python -m scripts.seed_admin` first."
            )

        user_role_result = await db.execute(select(Role).where(Role.name == "USER"))
        user_role = user_role_result.scalar_one_or_none()
        if user_role is None:
            raise SystemExit("USER role not found. Run `python -m scripts.seed_roles` first.")

        # --- Candidates ---
        candidates_by_email: dict[str, User] = {}
        for email, first_name, last_name, phone in CANDIDATES:
            candidates_by_email[email] = await _get_or_create_candidate(
                db, email, first_name, last_name, phone, user_role
            )
        await db.commit()

        # candidate_profile isn't loaded on the fresh User instances above until
        # we re-fetch, so grab CandidateProfile.id per user explicitly.
        profile_by_email: dict[str, CandidateProfile] = {}
        for email, user in candidates_by_email.items():
            result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
            profile_by_email[email] = result.scalar_one()

        # --- Jobs ---
        jobs_by_title: dict[str, Job] = {}
        for title, department, description in JOBS:
            jobs_by_title[title] = await _get_or_create_job(db, title, department, description, admin.id)
        await db.commit()

        # --- Interviews ---
        for (
            candidate_email, job_title, title, interview_type, status,
            scheduled_at, started_at, completed_at, overall_score,
        ) in INTERVIEWS:
            profile = profile_by_email[candidate_email]
            job = jobs_by_title[job_title]

            existing = await db.execute(
                select(Interview).where(Interview.candidate_id == profile.id, Interview.title == title)
            )
            if existing.scalar_one_or_none() is not None:
                print(f"Interview '{title}' for {candidate_email} already exists, skipping.")
                continue

            db.add(
                Interview(
                    job_id=job.id,
                    candidate_id=profile.id,
                    interviewer_id=admin.id,
                    title=title,
                    interview_type=interview_type,
                    difficulty="MEDIUM",
                    duration_minutes=45,
                    scheduled_at=scheduled_at,
                    status=status,
                    started_at=started_at,
                    completed_at=completed_at,
                    overall_score=overall_score,
                )
            )
            print(f"Created interview '{title}' for {candidate_email} ({status.value}).")
        await db.commit()

        # --- Resumes ---
        for candidate_email, file_name, file_type, uploaded_at, analyzed, summary in RESUMES:
            profile = profile_by_email[candidate_email]

            existing = await db.execute(
                select(Resume).where(Resume.candidate_id == profile.id, Resume.file_name == file_name)
            )
            if existing.scalar_one_or_none() is not None:
                print(f"Resume '{file_name}' already exists, skipping.")
                continue

            resume = Resume(
                candidate_id=profile.id,
                file_name=file_name,
                file_path=f"/seeded/{profile.id}/{file_name}",  # placeholder, no real file on disk
                file_type=file_type,
                file_size=204800,
                version=1,
                is_current=True,
                uploaded_at=uploaded_at,
            )
            db.add(resume)
            await db.flush()

            if analyzed:
                db.add(
                    ResumeAnalysis(
                        resume_id=resume.id,
                        raw_text=summary,
                        summary=summary,
                        total_experience=3.0,
                        current_role=None,
                        analysis_json={"summary": summary},
                        model_name="ollama",
                        prompt_version="seed-v1",
                    )
                )
            print(f"Created resume '{file_name}' ({'Analyzed' if analyzed else 'Processing'}).")
        await db.commit()

        print("\nDemo data seeded. Candidate login password for all seeded candidates:")
        print(f"  {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())