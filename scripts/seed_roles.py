"""
Run once after migrations, before anyone can register:

    python -m scripts.seed_roles

Creates the ADMIN, INTERVIEWER, and USER roles that app/services/auth_service.py
looks up by name.
"""
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.auth import Role

ROLES = [
    ("ADMIN", "Controls the platform: users, interviewers, AI/system settings, audit logs."),
    ("INTERVIEWER", "Creates jobs and interviews, reviews candidate performance and AI evaluations."),
    ("USER", "Candidate: manages profile/resume, takes AI interviews, views results."),
]


async def seed_roles() -> None:
    async with AsyncSessionLocal() as db:
        for name, description in ROLES:
            existing = await db.execute(select(Role).where(Role.name == name))
            if existing.scalar_one_or_none() is not None:
                print(f"Role '{name}' already exists, skipping.")
                continue
            db.add(Role(name=name, description=description))
            print(f"Created role '{name}'.")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_roles())
