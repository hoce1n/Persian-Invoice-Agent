"""System status and health details for operational visibility."""

import time
from pathlib import Path

from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.services.voice_agent_service import VoiceAgentService

router = APIRouter(tags=["status"])


def get_voice_agent_service() -> VoiceAgentService:
    return VoiceAgentService()


@router.get("/status")
def system_status(
    settings: Settings = Depends(get_settings),
    voice_agent_service: VoiceAgentService = Depends(get_voice_agent_service),
) -> dict:
    llm_configured = bool(settings.llm_api_key.strip())
    font_regular = Path(settings.pdf_font_regular_path)
    font_bold = Path(settings.pdf_font_bold_path)
    output_dir = Path(settings.pdf_output_dir)
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "checks": {
            "llm": {
                "status": "configured" if llm_configured else "missing_api_key",
                "base_url": settings.llm_base_url,
                "model": settings.llm_model,
            },
            "stt": {
                "status": "configured" if llm_configured else "missing_api_key",
                "model": settings.whisper_model,
            },
            "pdf": {
                "status": "configured" if font_regular.exists() and font_bold.exists() else "degraded",
                "output_dir": str(output_dir.resolve()),
                "font_regular": str(font_regular),
                "font_bold": str(font_bold),
            },
            "email": {
                "status": "simulated" if not settings.email_service_api_key.strip() else "configured",
                "manager_email": settings.manager_email,
            },
            "voice_agent": voice_agent_service.check_health(),
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
