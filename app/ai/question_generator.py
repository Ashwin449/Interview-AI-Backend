from app.ai.ollama_client import ollama_client

PROMPT_VERSION = "question-generation-v1"

SYSTEM_PROMPT = """You are an interview question generator. Given a single competency to test
(name, description, difficulty) and how many questions to produce, generate that many distinct
interview questions. Respond with ONLY valid JSON matching:

{
  "questions": [
    {
      "question_text": "string",
      "question_type": "CONCEPTUAL | TECHNICAL | SCENARIO | PROBLEM_SOLVING | BEHAVIORAL | DEBUGGING | SYSTEM_DESIGN",
      "difficulty": "EASY | MEDIUM | HARD",
      "expected_concepts": ["string"]
    }
  ]
}
"""

FOLLOW_UP_SYSTEM_PROMPT = """You are an adaptive interviewer. The candidate scored poorly on the
previous question. Given the original question, the candidate's answer, and which concepts they
missed, write ONE targeted follow-up question that probes the gap more specifically and simply.
Respond with ONLY valid JSON matching:

{
  "question_text": "string",
  "question_type": "FOLLOW_UP",
  "difficulty": "EASY | MEDIUM | HARD",
  "expected_concepts": ["string"]
}
"""


async def generate_questions_for_competency(
    competency_name: str, competency_description: str | None, difficulty: str | None, count: int
) -> tuple[dict, int]:
    user_prompt = (
        f"Competency: {competency_name}\n"
        f"Description: {competency_description or 'N/A'}\n"
        f"Difficulty: {difficulty or 'MEDIUM'}\n"
        f"Number of questions to generate: {count}\n"
    )
    parsed, elapsed_ms = await ollama_client.generate_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    return parsed, elapsed_ms


async def generate_follow_up_question(
    original_question: str, candidate_answer: str, missing_concepts: list[str]
) -> tuple[dict, int]:
    user_prompt = (
        f"Original question: {original_question}\n"
        f"Candidate's answer: {candidate_answer}\n"
        f"Missing/weak concepts: {missing_concepts}\n"
    )
    parsed, elapsed_ms = await ollama_client.generate_json(
        system_prompt=FOLLOW_UP_SYSTEM_PROMPT, user_prompt=user_prompt
    )
    return parsed, elapsed_ms
