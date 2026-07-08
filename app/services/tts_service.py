import logging
import time

import requests

from app.config.settings import Settings, get_settings
from app.core.errors import ErrorCode, map_provider_status, truncate

logger = logging.getLogger(__name__)


class TTSServiceError(Exception):
    """Raised when text-to-speech generation fails."""

    def __init__(self, message: str, *, status_code: int = 502, error_code: str = ErrorCode.UNEXPECTED) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class TTSService:
    """Convert Persian fallback text into audio via OpenAI-compatible API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._speech_url = f"{self._settings.llm_base_url.rstrip('/')}/audio/speech"

    def text_to_speech(self, text: str) -> bytes:
        if not text.strip():
            raise TTSServiceError("TTS input is empty", status_code=400, error_code=ErrorCode.UNEXPECTED)
        if not self._settings.llm_api_key.strip():
            raise TTSServiceError("API key not configured", status_code=500, error_code=ErrorCode.API_KEY_MISSING)

        payload = {
            "model": self._settings.tts_model,
            "voice": self._settings.tts_voice,
            "input": text,
            "response_format": "mp3",
        }
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "TTS fallback request | model=%s | voice=%s | chars=%d | preview=%s",
            self._settings.tts_model,
            self._settings.tts_voice,
            len(text),
            truncate(text, 180),
        )
        started = time.perf_counter()
        try:
            response = requests.post(
                self._speech_url,
                json=payload,
                headers=headers,
                timeout=self._settings.audio_timeout_seconds,
            )
            response.raise_for_status()
            audio_bytes = response.content
        except requests.Timeout as exc:
            logger.exception("TTS fallback timeout")
            raise TTSServiceError("TTS timeout", status_code=504, error_code=ErrorCode.UNEXPECTED) from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 502
            logger.error(
                "TTS fallback provider HTTP %s | body=%s",
                status_code,
                truncate(exc.response.text if exc.response is not None else "", 240),
            )
            raise TTSServiceError(
                f"TTS provider HTTP {status_code}",
                status_code=map_provider_status(status_code),
                error_code=ErrorCode.UNEXPECTED,
            ) from exc
        except requests.RequestException as exc:
            logger.exception("TTS fallback request failed")
            raise TTSServiceError("TTS unreachable", status_code=502, error_code=ErrorCode.UNEXPECTED) from exc

        elapsed_ms = (time.perf_counter() - started) * 1000
        if not audio_bytes:
            logger.error("TTS fallback empty audio | elapsed_ms=%.0f", elapsed_ms)
            raise TTSServiceError("TTS empty audio", status_code=502, error_code=ErrorCode.UNEXPECTED)

        logger.info("TTS fallback success | elapsed_ms=%.0f | bytes=%d", elapsed_ms, len(audio_bytes))
        return audio_bytes
