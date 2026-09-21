from app.ai.ollama_client import ollama_client

PROMPT_VERSION = "answer-evaluation-v1"

SYSTEM_PROMPT = """You are a strict but fair technical interview evaluator. Given a question,
the concepts it expects, and the candidate's transcribed answer, score the answer. Respond with
ONLY valid JSON matching:

{
  "overall_score": 7.8,
  "technical_score": 8.5,
  "relevance_score": 8.0,
  "completeness_score": 6.0,
  "reasoning_score": 7.0,
  "communication_score": 8.0,
  "strengths": ["string"],
  "weaknesses": ["string"],
  "missing_concepts": ["string"],
  "feedback": "2-3 sentences of constructive feedback",
  "needs_follow_up": true,
  "follow_up_reason": "string or null"
}

All scores are 0-10. needs_follow_up should be true when completeness_score or technical_score
is below 6, or when key expected concepts are missing.
"""


async def evaluate_answer(question_text: str, expected_concepts: list[str], answer_text: str) -> tuple[dict, int]:
    user_prompt = (
        f"Question: {question_text}\n"
        f"Expected concepts: {expected_concepts}\n"
        f"Candidate's answer: {answer_text}\n"
    )
    parsed, elapsed_ms = await ollama_client.generate_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    return parsed, elapsed_ms
