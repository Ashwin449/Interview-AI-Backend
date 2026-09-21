"""
Run once, after `python -m scripts.seed_roles`, to create your first admin login.

Interactive (safest - password isn't stored in your shell history):

    python -m scripts.seed_admin

Non-interactive, e.g. for CI or a fresh-environment setup script (set these in
your shell first, don't commit them anywhere):

    ADMIN_EMAIL=you@company.com ADMIN_PASSWORD=... python -m scripts.seed_admin

If the email already exists as a user, this promotes that existing account to
ADMIN instead of creating a duplicate.
"""
import asyncio
import getpass
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.auth import Role, User, UserRole


async def seed_admin(email: str, password: str, first_name: str, last_name: str) -> None:
    async with AsyncSessionLocal() as db:
        role_result = await db.execute(select(Role).where(Role.name == "ADMIN"))
        admin_role = role_result.scalar_one_or_none()
        if admin_role is None:
            raise SystemExit("ADMIN role not found. Run `python -m scripts.seed_roles` first.")

        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
            print(f"Created user '{email}'.")
        else:
            print(f"User '{email}' already exists - promoting to ADMIN (password left unchanged).")

        existing_role_link = await db.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == admin_role.id)
        )
        if existing_role_link.scalar_one_or_none() is None:
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))
            print(f"Assigned ADMIN role to '{email}'.")
        else:
            print(f"'{email}' already has the ADMIN role.")

        await db.commit()


def _read_credentials() -> tuple[str, str, str, str]:
    env_email = os.environ.get("ADMIN_EMAIL")
    env_password = os.environ.get("ADMIN_PASSWORD")

    if env_email and env_password:
        return env_email, env_password, "Admin", "User"

    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password (min 8 chars): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    first_name = input("First name [Admin]: ").strip() or "Admin"
    last_name = input("Last name [User]: ").strip() or "User"
    return email, password, first_name, last_name


if __name__ == "__main__":
    email, password, first_name, last_name = _read_credentials()
    asyncio.run(seed_admin(email, password, first_name, last_name))