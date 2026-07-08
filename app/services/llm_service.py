import json
import logging
import re
from typing import Any

import requests

from app.config.settings import Settings, get_settings
from app.core.errors import ErrorCode, api_error, map_provider_status, truncate
from app.prompts.invoice_extractor import SYSTEM_PROMPT
from app.schemas.invoice_schemas import InvoiceData

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _parse_json_content(content: str) -> dict[str, Any]:
    """Parse model output as JSON, stripping markdown fences if present."""
    text = content.strip()
    if not text:
        raise ValueError("Empty model response")

    block_match = _JSON_BLOCK_RE.search(text)
    if block_match:
        text = block_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _parse_gateway_error(response: requests.Response) -> str:
    """Extract a human-readable message from an OpenAI-compatible error response."""
    try:
        body = response.json()
        err = body.get("error", body)
        if isinstance(err, dict):
            msg = err.get("message", "")
            err_type = err.get("type", "")
            request_id = err.get("request_id", "")
            parts = [
                p
                for p in [
                    msg,
                    f"type={err_type}" if err_type else "",
                    f"request_id={request_id}" if request_id else "",
                ]
                if p
            ]
            if parts:
                return " — ".join(parts)
    except (json.JSONDecodeError, AttributeError):
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


class LLMServiceError(Exception):
    """Raised when the LLM gateway call fails or returns invalid data."""

    def __init__(self, message: str, *, status_code: int = 502, error_code: str = ErrorCode.LLM_PROVIDER) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class LLMService:
    """Extracts structured invoice data from Persian text via an OpenAI-compatible LLM gateway."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def extract_invoice_data(self, client_text: str) -> InvoiceData:
        """Call chat completions and parse the structured invoice JSON."""
        cleaned_text = client_text.strip()
        if not cleaned_text:
            raise LLMServiceError(
                "Invoice text is empty",
                status_code=422,
                error_code=ErrorCode.EMPTY_INPUT,
            )
        if not self._settings.llm_api_key:
            raise LLMServiceError(
                "API key not configured (LLM_API_KEY)",
                status_code=500,
                error_code=ErrorCode.API_KEY_MISSING,
            )

        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": cleaned_text},
            ],
            "temperature": self._settings.llm_temperature,
        }
        logger.info(
            "Invoice extraction request | model=%s | chars=%d | preview=%s",
            self._settings.llm_model,
            len(cleaned_text),
            truncate(cleaned_text, 240),
        )

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self._settings.llm_timeout_seconds)
            response.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else "unknown"
            detail = _parse_gateway_error(response) if response is not None else str(exc)
            logger.error("LLM gateway request failed with status=%s: %s", status_code, detail)
            mapped_status = map_provider_status(response.status_code) if response is not None else 502
            error_code = ErrorCode.LLM_RATE_LIMIT if response is not None and response.status_code == 429 else ErrorCode.LLM_PROVIDER
            raise LLMServiceError(
                f"AI Service Error ({status_code}): {detail}",
                status_code=mapped_status,
                error_code=error_code,
            ) from exc
        except requests.Timeout as exc:
            logger.error("LLM timeout after %.1f seconds", self._settings.llm_timeout_seconds)
            raise LLMServiceError(
                "AI extraction timeout",
                status_code=504,
                error_code=ErrorCode.LLM_TIMEOUT,
            ) from exc
        except requests.RequestException as exc:
            logger.exception("LLM gateway request failed")
            raise LLMServiceError(
                f"AI Service Error: {exc}",
                status_code=502,
                error_code=ErrorCode.LLM_UNREACHABLE,
            ) from exc

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw_data = _parse_json_content(content)
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            logger.exception("Failed to parse LLM gateway response")
            raise LLMServiceError(
                "Invalid response from AI provider",
                status_code=502,
                error_code=ErrorCode.LLM_INVALID_RESPONSE,
            ) from exc

        try:
            model = InvoiceData.model_validate(raw_data)
            logger.info(
                "Invoice extraction success | client=%s | amount=%.2f | currency=%s",
                model.client_name,
                model.payable_amount or model.amount,
                model.currency.value,
            )
            return model
        except Exception as exc:
            logger.exception("Extracted data failed schema validation")
            raise LLMServiceError(
                f"Extracted data is invalid: {exc}",
                status_code=422,
                error_code=ErrorCode.EXTRACTION_FAILED,
            ) from exc

    @staticmethod
    def as_http_exception(exc: LLMServiceError) -> Exception:
        return api_error(exc.status_code, exc.error_code, message=str(exc))
