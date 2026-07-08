"""Central logging configuration for the Persian Invoice Agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config.settings import Settings

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(settings: Settings | None = None) -> None:
    """Configure root logging once with a clear production-friendly format."""
    if settings is None:
        from app.config.settings import get_settings

        settings = get_settings()

    effective_level = "DEBUG" if settings.debug else settings.log_level
    logging.basicConfig(
        level=effective_level,
        format=settings.log_format,
        datefmt=settings.log_date_format,
        force=True,
    )

    if effective_level != "DEBUG":
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger(__name__).debug(
        "Logging configured | level=%s | app=%s",
        settings.log_level,
        settings.app_name,
    )
