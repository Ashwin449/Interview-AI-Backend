import json
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import AIServiceError

settings = get_settings()


class OllamaClient:
    """Thin wrapper around the local Ollama HTTP API (/api/generate)."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        timeout_seconds: float = 120.0,
    ) -> tuple[dict[str, Any], int]:
        """
        Calls Ollama asking for a strict JSON response.
        Returns (parsed_json, execution_time_ms). Raises AIServiceError on failure.
        """
        start = time.monotonic()
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIServiceError(f"Ollama request failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        body = response.json()
        raw_text = body.get("response", "")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"Ollama returned non-JSON output: {exc}") from exc

        return parsed, elapsed_ms

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        timeout_seconds: float = 60.0,
    ) -> tuple[str, int]:
        start = time.monotonic()
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIServiceError(f"Ollama request failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return response.json().get("response", ""), elapsed_ms


ollama_client = OllamaClient()
