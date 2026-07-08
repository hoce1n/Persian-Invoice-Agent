import logging
import time
from io import BytesIO

import requests

from app.config.settings import Settings, get_settings
from app.core.errors import ErrorCode
from app.core.messages import STT_RATE_LIMIT_FALLBACK_MESSAGE, STT_TIMEOUT_FALLBACK_MESSAGE

logger = logging.getLogger(__name__)


class STTServiceError(Exception):
    """Raised when speech-to-text transcription fails."""

    def __init__(self, message: str, *, status_code: int = 502, error_code: str = ErrorCode.STT_PROVIDER) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class STTService:
    """Transcribes Persian voice input via an OpenAI-compatible Whisper endpoint."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to Persian text."""
        if not audio_bytes:
            raise STTServiceError("Audio file is empty", status_code=422, error_code=ErrorCode.EMPTY_AUDIO)

        if self._settings.llm_api_key:
            return self._transcribe_via_gateway(audio_bytes, filename)

        return self._transcribe_mock(audio_bytes, filename)

    def _transcribe_via_gateway(self, audio_bytes: bytes, filename: str) -> str:
        url = f"{self._settings.llm_base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}
        data = {
            "model": self._settings.whisper_model,
            "language": "fa",
            "response_format": "json",
        }
        max_attempts = max(1, self._settings.stt_max_retries + 1)
        timeout_attempts = 0
        max_timeout_attempts = 2

        for attempt in range(1, max_attempts + 1):
            files = {"file": (filename, BytesIO(audio_bytes))}
            try:
                started = time.perf_counter()
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self._settings.stt_timeout_seconds,
                )
                if response.status_code == 429:
                    if attempt < max_attempts:
                        backoff_seconds = min(3.0, self._settings.stt_retry_delay * (2 ** (attempt - 1)))
                        logger.warning(
                            "STT rate limited | attempt=%d/%d | sleep=%.1fs",
                            attempt,
                            max_attempts,
                            backoff_seconds,
                        )
                        time.sleep(backoff_seconds)
                        continue
                    logger.error("STT rate limited after retries | returning graceful fallback")
                    return STT_RATE_LIMIT_FALLBACK_MESSAGE

                if response.status_code == 504:
                    if attempt < max_attempts:
                        backoff_seconds = min(3.0, self._settings.stt_retry_delay * (2 ** (attempt - 1)))
                        logger.warning(
                            "STT gateway 504 | attempt=%d/%d | sleep=%.1fs",
                            attempt,
                            max_attempts,
                            backoff_seconds,
                        )
                        time.sleep(backoff_seconds)
                        continue
                    logger.error("STT gateway 504 after retries | returning graceful fallback")
                    return STT_TIMEOUT_FALLBACK_MESSAGE

                response.raise_for_status()
                body = response.json()
                text = body.get("text", "").strip()
                if not text:
                    raise STTServiceError("Transcription returned empty text", error_code=ErrorCode.STT_EMPTY)
                logger.info(
                    "Audio transcribed via AI gateway | attempt=%d | elapsed_ms=%.0f | chars=%d",
                    attempt,
                    (time.perf_counter() - started) * 1000,
                    len(text),
                )
                return text
            except requests.exceptions.ReadTimeout:
                timeout_attempts += 1
                if timeout_attempts < max_timeout_attempts:
                    logger.warning(
                        "STT read timeout | attempt=%d/%d | timeout=%.1fs",
                        timeout_attempts,
                        max_timeout_attempts,
                        self._settings.stt_timeout_seconds,
                    )
                    time.sleep(min(3.0, self._settings.stt_retry_delay))
                    continue
                logger.error("STT read timeout after retry | returning graceful fallback")
                return STT_TIMEOUT_FALLBACK_MESSAGE
            except requests.Timeout:
                timeout_attempts += 1
                if timeout_attempts < max_timeout_attempts:
                    logger.warning(
                        "STT timeout | attempt=%d/%d | timeout=%.1fs",
                        timeout_attempts,
                        max_timeout_attempts,
                        self._settings.stt_timeout_seconds,
                    )
                    time.sleep(min(3.0, self._settings.stt_retry_delay))
                    continue
                logger.error("STT timeout after retry | returning graceful fallback")
                return STT_TIMEOUT_FALLBACK_MESSAGE
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else 502
                if status_code >= 500:
                    if attempt < max_attempts:
                        backoff_seconds = min(3.0, self._settings.stt_retry_delay * (2 ** (attempt - 1)))
                        logger.warning(
                            "STT gateway HTTP %s | attempt=%d/%d | sleep=%.1fs",
                            status_code,
                            attempt,
                            max_attempts,
                            backoff_seconds,
                        )
                        time.sleep(backoff_seconds)
                        continue
                    logger.error("STT gateway HTTP %s after retries | returning graceful fallback", status_code)
                    return STT_TIMEOUT_FALLBACK_MESSAGE

                mapped_status = 429 if status_code == 429 else 502
                code = ErrorCode.STT_RATE_LIMIT if status_code == 429 else ErrorCode.STT_PROVIDER
                logger.exception("Speech-to-text gateway returned HTTP %s", status_code)
                raise STTServiceError(f"AI Service Error ({status_code})", status_code=mapped_status, error_code=code) from exc
            except requests.RequestException as exc:
                logger.exception("Speech-to-text gateway request failed")
                raise STTServiceError(
                    f"AI Service Error: {exc}",
                    status_code=502,
                    error_code=ErrorCode.STT_UNREACHABLE,
                ) from exc

        logger.error("STT retry loop ended without result, returning fallback")
        return STT_TIMEOUT_FALLBACK_MESSAGE

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
