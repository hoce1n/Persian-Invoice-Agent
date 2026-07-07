import logging
from io import BytesIO

import requests

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class STTServiceError(Exception):
    """Raised when speech-to-text transcription fails."""


class STTService:
    """Transcribes Persian voice input via an OpenAI-compatible Whisper endpoint."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to Persian text."""
        if not audio_bytes:
            raise STTServiceError("Audio file is empty")

        if self._settings.llm_api_key:
            return self._transcribe_via_gateway(audio_bytes, filename)

        return self._transcribe_mock(audio_bytes, filename)

    def _transcribe_via_gateway(self, audio_bytes: bytes, filename: str) -> str:
        url = f"{self._settings.llm_base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}
        files = {"file": (filename, BytesIO(audio_bytes))}
        data = {
            "model": self._settings.whisper_model,
            "language": "fa",
            "response_format": "json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
            response.raise_for_status()
            body = response.json()
            text = body.get("text", "").strip()
            if not text:
                raise STTServiceError("Transcription returned empty text")
            logger.info("Audio transcribed via AI gateway (%d chars)", len(text))
            return text
        except requests.RequestException as exc:
            logger.exception("Speech-to-text gateway request failed")
            raise STTServiceError(f"AI Service Error: {exc}") from exc

    def _transcribe_mock(self, audio_bytes: bytes, filename: str) -> str:
        """Development fallback when no API key is configured."""
        logger.warning(
            "LLM_API_KEY not set — using mock transcription for %s (%d bytes)",
            filename,
            len(audio_bytes),
        )
        return (
            "فاکتور برای آقای رضایی بابت مشاوره فنی، "
            "مبلغ ۵ میلیون تومان"
        )
