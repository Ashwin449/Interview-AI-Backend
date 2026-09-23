import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:admin@localhost:5432/intervueai"

async def reset():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
    await engine.dispose()
    print("Schema reset done.")

asyncio.run(reset())
