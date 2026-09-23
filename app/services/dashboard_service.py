from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.candidate import CandidateProfile
from app.models.enums import InterviewStatus
from app.models.interview import Interview
from app.schemas.admin_views import (
    ActivityPoint,
    DashboardSummaryResponse,
    RecentInterviewItem,
    UpcomingInterviewItem,
)

_STATUS_LABELS: dict[InterviewStatus, str] = {
    InterviewStatus.SCHEDULED: "Scheduled",
    InterviewStatus.IN_PROGRESS: "In Progress",
    InterviewStatus.COMPLETED: "Completed",
    InterviewStatus.CANCELLED: "Cancelled",
}


def _initials(user: User) -> str:
    first = (user.first_name or "")[:1]
    last = (user.last_name or "")[:1]
    return f"{first}{last}".upper()


def _full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def _format_time(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%I:%M %p").lstrip("0")


def _format_date(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y")


async def get_summary(db: AsyncSession, upcoming_limit: int = 5, recent_limit: int = 5) -> DashboardSummaryResponse:
    # --- Status counts ---
    counts_result = await db.execute(
        select(Interview.status, func.count(Interview.id)).group_by(Interview.status)
    )
    counts_by_status = {status: count for status, count in counts_result.all()}
    total_interviews = sum(counts_by_status.values())
    completed = counts_by_status.get(InterviewStatus.COMPLETED, 0)
    in_progress = counts_by_status.get(InterviewStatus.IN_PROGRESS, 0)
    scheduled = counts_by_status.get(InterviewStatus.SCHEDULED, 0)
    cancelled = counts_by_status.get(InterviewStatus.CANCELLED, 0)

    # --- Average score across scored interviews ---
    avg_result = await db.execute(
        select(func.avg(Interview.overall_score)).where(Interview.overall_score.is_not(None))
    )
    avg_score = avg_result.scalar_one_or_none()
    average_score = round(float(avg_score), 1) if avg_score is not None else None

    # --- Activity: interviews per day, last 7 days (by created_at) ---
    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=6)

    activity_result = await db.execute(
        select(func.date(Interview.created_at), func.count(Interview.id))
        .where(func.date(Interview.created_at) >= window_start)
        .group_by(func.date(Interview.created_at))
    )
    counts_by_day = {day: count for day, count in activity_result.all()}

    activity = [
        ActivityPoint(
            date=day,
            day_label=day.strftime("%a"),
            count=counts_by_day.get(day, 0),
        )
        for day in (window_start + timedelta(days=i) for i in range(7))
    ]

    # --- Upcoming interviews (next scheduled, soonest first) ---
    upcoming_result = await db.execute(
        select(Interview, User)
        .join(CandidateProfile, CandidateProfile.id == Interview.candidate_id)
        .join(User, User.id == CandidateProfile.user_id)
        .where(Interview.status == InterviewStatus.SCHEDULED)
        .order_by(Interview.scheduled_at.asc().nulls_last())
        .limit(upcoming_limit)
    )
    upcoming_rows = upcoming_result.all()
    upcoming_interviews = [
        UpcomingInterviewItem(
            id=interview.id,
            candidate=_full_name(user),
            initials=_initials(user),
            role=interview.title,
            time=_format_time(interview.scheduled_at),
            is_next=(index == 0),
        )
        for index, (interview, user) in enumerate(upcoming_rows)
    ]

    # --- Recent interviews (most recently created first) ---
    recent_result = await db.execute(
        select(Interview, User)
        .join(CandidateProfile, CandidateProfile.id == Interview.candidate_id)
        .join(User, User.id == CandidateProfile.user_id)
        .order_by(Interview.created_at.desc())
        .limit(recent_limit)
    )
    recent_interviews = [
        RecentInterviewItem(
            id=interview.id,
            candidate=_full_name(user),
            initials=_initials(user),
            role=interview.title,
            date=_format_date(interview.created_at),
            score=float(interview.overall_score) if interview.overall_score is not None else None,
            status=_STATUS_LABELS.get(interview.status, str(interview.status)),
        )
        for interview, user in recent_result.all()
    ]

    return DashboardSummaryResponse(
        total_interviews=total_interviews,
        completed=completed,
        in_progress=in_progress,
        scheduled=scheduled,
        cancelled=cancelled,
        average_score=average_score,
        activity=activity,
        upcoming_interviews=upcoming_interviews,
        recent_interviews=recent_interviews,
    )