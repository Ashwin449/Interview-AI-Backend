from app.ai.ollama_client import ollama_client

PROMPT_VERSION = "report-generation-v1"

SYSTEM_PROMPT = """You are writing the final hiring report for an AI-conducted technical interview.
Given per-competency scores and evaluation summaries across all answers, produce a hiring
recommendation. Respond with ONLY valid JSON matching:

{
  "summary": "3-4 sentence overall summary",
  "overall_score": 7.6,
  "technical_score": 7.8,
  "problem_solving": 7.0,
  "communication_score": 8.0,
  "strengths": ["string"],
  "weaknesses": ["string"],
  "recommendations": ["string - what the candidate should improve"],
  "recommendation": "STRONG_HIRE | HIRE | MAYBE | NO_HIRE"
}
"""


async def generate_interview_report(competency_scores: list[dict], answer_evaluations: list[dict]) -> tuple[dict, int]:
    user_prompt = (
        f"Competency scores: {competency_scores}\n"
        f"Per-answer evaluations: {answer_evaluations}\n"
    )
    parsed, elapsed_ms = await ollama_client.generate_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    return parsed, elapsed_ms
