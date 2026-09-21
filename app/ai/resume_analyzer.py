from app.ai.ollama_client import ollama_client

PROMPT_VERSION = "resume-analysis-v1"

SYSTEM_PROMPT = """You are a resume analysis engine for a technical interview platform.
Given raw resume text, extract structured data. Respond with ONLY valid JSON, no prose,
matching exactly this shape:

{
  "summary": "2-3 sentence professional summary",
  "total_experience_years": 3.5,
  "current_role": "string or null",
  "skills": [{"name": "Angular", "level": "Advanced", "years": 2}],
  "projects": [{"name": "string", "description": "string"}],
  "responsibilities": ["string"],
  "technologies": ["string"],
  "experience": [
    {
      "company_name": "string",
      "job_title": "string",
      "start_date": "YYYY-MM-DD or null",
      "end_date": "YYYY-MM-DD or null",
      "is_current": false,
      "description": "string"
    }
  ]
}
"""


async def analyze_resume_text(raw_text: str) -> tuple[dict, int]:
    """Returns (analysis_json, execution_time_ms)."""
    truncated = raw_text[:12000]  # keep prompts within a safe context window
    parsed, elapsed_ms = await ollama_client.generate_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Resume text:\n\n{truncated}",
    )
    return parsed, elapsed_ms
