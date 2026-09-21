from app.ai.ollama_client import ollama_client

PROMPT_VERSION = "blueprint-generation-v1"

SYSTEM_PROMPT = """You are an interview design engine. Given a candidate's resume analysis,
a job's required skills (with importance weights), and the requested interview type/duration,
design a blueprint of competencies to evaluate. Respond with ONLY valid JSON matching:

{
  "competencies": [
    {
      "name": "Angular",
      "description": "short description of what this competency covers",
      "weight": 40,
      "question_count": 5,
      "difficulty": "MEDIUM",
      "priority": 1,
      "rubric_criteria": [
        {"name": "Technical Accuracy", "weight": 40},
        {"name": "Concept Coverage", "weight": 30},
        {"name": "Practical Understanding", "weight": 20},
        {"name": "Communication", "weight": 10}
      ]
    }
  ]
}

Weights across competencies must sum to 100. Total question_count across competencies
must equal the requested total_questions.
"""


async def generate_blueprint(
    job_skills: list[dict],
    resume_summary: str | None,
    interview_type: str,
    difficulty: str | None,
    total_questions: int,
) -> tuple[dict, int]:
    user_prompt = (
        f"Interview type: {interview_type}\n"
        f"Difficulty: {difficulty or 'MEDIUM'}\n"
        f"Total questions requested: {total_questions}\n"
        f"Job required skills (name, weight): {job_skills}\n"
        f"Candidate resume summary: {resume_summary or 'Not available'}\n"
    )
    parsed, elapsed_ms = await ollama_client.generate_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    return parsed, elapsed_ms
