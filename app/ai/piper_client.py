import asyncio
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AIServiceError

settings = get_settings()


class PiperClient:
    """Wraps the local piper CLI binary for real text-to-speech synthesis."""

    async def synthesize(self, text: str, output_dir: str | None = None) -> str:
        """
        Runs piper against the configured voice model and writes a .wav file.
        Returns the path to the generated audio file.
        """
        out_dir = Path(output_dir or settings.audio_storage_dir) / "tts"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{uuid.uuid4()}.wav"

        command = [
            settings.piper_binary_path,
            "--model",
            settings.piper_voice_model_path,
            "--output_file",
            str(output_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate(input=text.encode("utf-8"))
        except FileNotFoundError as exc:
            raise AIServiceError(f"Piper binary not found at {settings.piper_binary_path}") from exc

        if process.returncode != 0:
            raise AIServiceError(f"Piper synthesis failed: {stderr.decode('utf-8', errors='ignore')}")

        return str(output_path)


piper_client = PiperClient()
