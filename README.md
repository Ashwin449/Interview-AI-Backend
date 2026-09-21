# IntervueAI Backend

FastAPI + PostgreSQL backend for the IntervueAI adaptive AI interview platform, with
real local AI integration (Ollama for the LLM, faster-whisper for speech-to-text,
Piper for text-to-speech).

## Architecture

```
Angular  ->  FastAPI  ->  Interview Engine
                            ├── PostgreSQL   (truth)
                            └── AI Services  (intelligence)
                                  ├── Ollama   (LLM: analysis, blueprints, questions, evaluation, reports)
                                  ├── Whisper  (speech-to-text)
                                  └── Piper    (text-to-speech)
```

All 27 tables from the design doc are modeled under `app/models/`, grouped exactly
as specified: auth, candidate, job, interview (design + execution), evaluation, AI
tracking, admin.

## 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- [Ollama](https://ollama.com) running locally with a model pulled, e.g.:
  ```
  ollama pull llama3.1:8b
  ```
- [Piper](https://github.com/rhasspy/piper) binary + a voice model (`.onnx`) downloaded
- `faster-whisper` will download its model weights on first use (no separate install
  needed beyond the pip package already in `requirements.txt`)

## 2. Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL / DATABASE_URL_SYNC, JWT_SECRET_KEY,
# OLLAMA_MODEL, PIPER_BINARY_PATH, PIPER_VOICE_MODEL_PATH

createdb intervueai   # or create the DB however you prefer
```

## 3. Run migrations

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## 4. Seed roles (required before anyone can register)

```bash
python -m scripts.seed_roles
```

This creates the `ADMIN`, `INTERVIEWER`, and `USER` rows in the `roles` table.
`/api/auth/register` looks up the role by name and will 404 until this has run.

To create your first admin: register normally with `"role": "USER"` disabled and
`"role": "ADMIN"` set in the request body (there's no public admin-signup gate here —
add one, or promote a user via direct SQL / a follow-up admin endpoint, before this
goes anywhere near production).

## 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## Endpoint map

| Area | Routes |
|---|---|
| Auth | `POST /api/auth/register`, `/login`, `/refresh`, `/logout`, `GET /me` |
| Candidate profile | `GET/PATCH /api/users/me/profile` |
| Resumes | `POST /api/resumes/upload`, `POST /api/resumes/{id}/analyze`, `GET /api/resumes/me` |
| Jobs | `POST/GET /api/jobs`, `GET /api/jobs/{id}`, `POST /api/jobs/{id}/invite` |
| Interviews | `POST/GET /api/interviews/{id}`, `POST /api/interviews/{id}/blueprint`, `POST /api/interviews/{id}/questions`, `GET /api/interviews/{id}/report` |
| Live sessions | `POST /api/sessions/{interview_id}/start`, `GET /api/sessions/{token}`, `POST /api/sessions/{token}/answers/text`, `POST /api/sessions/{token}/answers/audio` |
| Admin | `GET /api/admin/users`, `PATCH /api/admin/users/{id}/active`, `POST /api/admin/roles/assign`, `GET /api/admin/audit-logs`, `GET/PUT /api/admin/settings` |

## The interview flow, end to end

1. Candidate registers (`role: USER`) → a `candidate_profiles` row is created automatically.
2. Candidate uploads a resume → `POST /api/resumes/upload`, then `POST /api/resumes/{id}/analyze`
   calls Ollama, extracts skills/experience, and folds them into `candidate_skills` /
   `candidate_experience`.
3. Interviewer creates a job with weighted required skills → `POST /api/jobs`.
4. Interviewer creates an interview for a candidate → `POST /api/interviews`.
5. Interviewer generates the blueprint → `POST /api/interviews/{id}/blueprint` (Ollama designs
   competencies + rubrics, weighted to sum to 100).
6. Interviewer generates questions → `POST /api/interviews/{id}/questions` (Ollama writes
   questions per competency).
7. Candidate starts the session → `POST /api/sessions/{interview_id}/start`.
8. Candidate answers each question via text or audio:
   - Audio path: file saved → **Whisper** transcribes → transcript stored → evaluated.
   - Every answer is scored by **Ollama** (`answer_evaluator`). If the score is weak,
     the engine generates one adaptive follow-up question before moving on
     (`parent_question_id` links it back).
9. When the plan is exhausted, the session auto-completes: per-competency scores are
   aggregated, and Ollama generates the final `interview_reports` row (summary,
   strengths/weaknesses, hire recommendation).
10. Interviewer/candidate view the report → `GET /api/interviews/{id}/report`.

Every AI call (resume analysis, blueprint, questions, evaluation, follow-ups, reports)
is logged to `ai_runs` with model name, prompt version, timing, and input/output —
so you can always answer "which model generated this?" and "why did this fail?".

## What's intentionally NOT built yet

This is a complete, running backbone — not a finished product. Known gaps to fill in
next:
- Rate limiting / request throttling on the Ollama-backed endpoints (LLM calls are slow;
  consider a job queue for blueprint/question generation on larger interviews)
- Email verification flow (`is_verified` exists on `User` but nothing sets it yet)
- Pagination on list endpoints (`/api/jobs`, `/api/admin/users`, `/api/admin/audit-logs`)
- Fine-grained authorization (e.g. an interviewer should probably only manage their own
  jobs/interviews — this version only checks role, not ownership)
- Automated tests
- Ollama/Whisper/Piper failures are surfaced as clean 502s (`AIServiceError`) but there's
  no retry/backoff yet
