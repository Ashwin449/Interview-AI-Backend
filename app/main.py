import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, dashboard, interviews, jobs, resumes, sessions, users
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intervueai")

app = FastAPI(
    title="IntervueAI API",
    version="1.0.0",
    description="Backend for the IntervueAI adaptive AI interview practice platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(interviews.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(dashboard.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
