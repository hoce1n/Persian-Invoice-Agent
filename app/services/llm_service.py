import json
import logging
from typing import Any

import requests

from app.config.settings import Settings, get_settings
from app.prompts.invoice_extractor import SYSTEM_PROMPT
from app.schemas.invoice_schemas import InvoiceData

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised when the Bynara LLM call fails or returns invalid data."""


class LLMService:
    """Extracts structured invoice data from Persian text via the Bynara LLM router."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def extract_invoice_data(self, client_text: str) -> InvoiceData:
        """Call Bynara chat completions and parse the structured invoice JSON."""
        if not self._settings.bynara_api_key:
            raise LLMServiceError("BYNARA_API_KEY is not configured")

        url = f"{self._settings.bynara_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.bynara_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._settings.bynara_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": client_text.strip()},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Bynara API request failed")
            raise LLMServiceError(f"Bynara API request failed: {exc}") from exc

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw_data = json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.exception("Failed to parse Bynara response")
            raise LLMServiceError("Invalid response from Bynara API") from exc

        try:
            return InvoiceData.model_validate(raw_data)
        except Exception as exc:
            logger.exception("Extracted data failed schema validation")
            raise LLMServiceError(f"Extracted data is invalid: {exc}") from exc
