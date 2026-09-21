import enum


class RoleName(str, enum.Enum):
    ADMIN = "ADMIN"
    INTERVIEWER = "INTERVIEWER"
    USER = "USER"


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class JobCandidateStatus(str, enum.Enum):
    INVITED = "INVITED"
    APPLIED = "APPLIED"
    INTERVIEW_PENDING = "INTERVIEW_PENDING"
    INTERVIEWED = "INTERVIEWED"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"


class InterviewType(str, enum.Enum):
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    HR = "HR"
    MIXED = "MIXED"
    CODING = "CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BlueprintStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class QuestionType(str, enum.Enum):
    CONCEPTUAL = "CONCEPTUAL"
    TECHNICAL = "TECHNICAL"
    SCENARIO = "SCENARIO"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    BEHAVIORAL = "BEHAVIORAL"
    DEBUGGING = "DEBUGGING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    FOLLOW_UP = "FOLLOW_UP"


class SessionStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class AnswerType(str, enum.Enum):
    TEXT = "TEXT"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Recommendation(str, enum.Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    MAYBE = "MAYBE"
    NO_HIRE = "NO_HIRE"


class AIOperation(str, enum.Enum):
    RESUME_ANALYSIS = "RESUME_ANALYSIS"
    BLUEPRINT_GENERATION = "BLUEPRINT_GENERATION"
    QUESTION_GENERATION = "QUESTION_GENERATION"
    ANSWER_EVALUATION = "ANSWER_EVALUATION"
    FOLLOW_UP_GENERATION = "FOLLOW_UP_GENERATION"
    REPORT_GENERATION = "REPORT_GENERATION"


class AIRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
