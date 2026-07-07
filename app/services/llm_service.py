import json
import logging
import re
from typing import Any

import requests

from app.config.settings import Settings, get_settings
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


class LLMService:
    """Extracts structured invoice data from Persian text via an OpenAI-compatible LLM gateway."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def extract_invoice_data(self, client_text: str) -> InvoiceData:
        """Call chat completions and parse the structured invoice JSON."""
        if not self._settings.llm_api_key:
            raise LLMServiceError("API key not configured (LLM_API_KEY)")

        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": client_text.strip()},
            ],
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else "unknown"
            detail = _parse_gateway_error(response) if response is not None else str(exc)
            logger.error("LLM gateway request failed with status=%s: %s", status_code, detail)
            raise LLMServiceError(f"AI Service Error ({status_code}): {detail}") from exc
        except requests.RequestException as exc:
            logger.exception("LLM gateway request failed")
            raise LLMServiceError(f"AI Service Error: {exc}") from exc

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw_data = _parse_json_content(content)
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            logger.exception("Failed to parse LLM gateway response")
            raise LLMServiceError("Invalid response from AI provider") from exc

        try:
            return InvoiceData.model_validate(raw_data)
        except Exception as exc:
            logger.exception("Extracted data failed schema validation")
            raise LLMServiceError(f"Extracted data is invalid: {exc}") from exc
