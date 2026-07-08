"""Downstream health checks for the Persian Voice Agent sister service."""

from __future__ import annotations

import logging
import time

import requests

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class VoiceAgentService:
    """Ping the Voice Agent for cross-service health visibility."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def check_health(self) -> dict[str, str | int | float | None]:
        health_url = f"{self._settings.voice_agent_url.rstrip('/')}/health"
        started = time.perf_counter()
        try:
            response = requests.get(
                health_url,
                timeout=min(self._settings.voice_agent_timeout_seconds, 5.0),
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            if response.ok:
                detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                return {
                    "status": "connected",
                    "url": health_url,
                    "latency_ms": elapsed_ms,
                    "detail": detail,
                }
            return {
                "status": "degraded",
                "url": health_url,
                "latency_ms": elapsed_ms,
                "detail": f"HTTP {response.status_code}",
            }
        except requests.RequestException as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.warning("Voice Agent health check failed | url=%s | error=%s", health_url, exc)
            return {
                "status": "unreachable",
                "url": health_url,
                "latency_ms": elapsed_ms,
                "detail": str(exc),
            }
