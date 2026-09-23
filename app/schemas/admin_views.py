import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import InterviewStatus, InterviewType


# ---------- Interviews list (GET /api/interviews) ----------

class InterviewListItemResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    initials: str
    role: str
    interview_type: InterviewType
    scheduled_at: datetime | None
    status: InterviewStatus
    score: float | None

    class Config:
        from_attributes = True


class InterviewListResponse(BaseModel):
    items: list[InterviewListItemResponse]
    total: int


# ---------- Admin resumes list (GET /api/resumes) ----------

class ResumeAdminListItemResponse(BaseModel):
    id: uuid.UUID
    candidate_name: str
    initials: str
    file_name: str
    uploaded_on: datetime
    status: str

    class Config:
        from_attributes = True


class ResumeAdminListResponse(BaseModel):
    items: list[ResumeAdminListItemResponse]
    total: int


# ---------- Dashboard summary (GET /api/dashboard/summary) ----------

class ActivityPoint(BaseModel):
    date: date
    day_label: str
    count: int


class UpcomingInterviewItem(BaseModel):
    id: uuid.UUID
    candidate: str        # was candidate_name
    initials: str
    role: str
    time: str             # was scheduled_at: datetime | None — now pre-formatted "HH:MM" or "—"
    is_next: bool          # new — computed by the service (first item = True)


class RecentInterviewItem(BaseModel):
    id: uuid.UUID
    candidate: str         # was candidate_name
    initials: str
    role: str
    date: str              # was created_at: datetime — now pre-formatted "MMM D, YYYY"
    score: float | None
    status: str            # was InterviewStatus — now display string "Completed" / "In Progress" / etc.


class DashboardSummaryResponse(BaseModel):
    total_interviews: int
    completed: int
    in_progress: int
    scheduled: int
    cancelled: int
    average_score: float | None
    activity: list[ActivityPoint]
    upcoming_interviews: list[UpcomingInterviewItem]
    recent_interviews: list[RecentInterviewItem]