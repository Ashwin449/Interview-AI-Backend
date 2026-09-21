import time
from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import AIServiceError

settings = get_settings()


@lru_cache
def _get_model():
    # Imported lazily so the API can boot even if faster-whisper / its native
    # deps aren't installed in an environment that only needs the text path.
    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type="int8" if settings.whisper_device == "cpu" else "float16",
    )


class WhisperClient:
    """Wraps faster-whisper for local, real speech-to-text transcription."""

    def transcribe(self, audio_path: str) -> tuple[str, str | None, float | None, int]:
        """
        Returns (transcript_text, detected_language, avg_confidence, processing_time_ms).
        """
        start = time.monotonic()
        try:
            model = _get_model()
            segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
            segments = list(segments)
        except Exception as exc:  # noqa: BLE001 - surfaced as a clean 502 to the client
            raise AIServiceError(f"Whisper transcription failed: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        avg_logprob = (
            sum(segment.avg_logprob for segment in segments) / len(segments) if segments else None
        )
        # avg_logprob is a log-probability (<= 0); convert to a rough 0-1 confidence proxy.
        confidence = round(min(1.0, max(0.0, 1.0 + avg_logprob)), 3) if avg_logprob is not None else None

        return text, info.language, confidence, elapsed_ms


whisper_client = WhisperClient()
