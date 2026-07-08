from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Persian Invoice Agent"
    app_version: str = "0.2.0"
    app_env: str = "development"
    app_base_url: str = "http://localhost:8001"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = False

    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    whisper_model: str = Field(default="whisper-1", alias="WHISPER_MODEL")
    stt_timeout_seconds: float = Field(default=45.0, alias="STT_TIMEOUT_SECONDS")
    stt_max_retries: int = Field(default=2, alias="STT_MAX_RETRIES")
    stt_retry_delay: float = Field(default=1.0, alias="STT_RETRY_DELAY")
    tts_model: str = Field(default="gpt-4o-mini-tts", alias="TTS_MODEL")
    tts_voice: str = Field(default="alloy", alias="TTS_VOICE")
    audio_timeout_seconds: float = Field(default=60.0, alias="AUDIO_TIMEOUT_SECONDS")

    email_service_api_key: str = Field(default="", alias="EMAIL_SERVICE_API_KEY")
    email_from_address: str = Field(default="invoices@example.com", alias="EMAIL_FROM_ADDRESS")
    email_approval_recipient: str = Field(default="approver@example.com", alias="EMAIL_APPROVAL_RECIPIENT")
    manager_email: str = Field(default="manager@example.com", alias="MANAGER_EMAIL")
    default_client_email: str = Field(default="client@example.com", alias="DEFAULT_CLIENT_EMAIL")

    pdf_output_dir: str = Field(default="./generated_invoices", alias="PDF_OUTPUT_DIR")
    pdf_font_regular_path: str = Field(
        default="./app/assets/fonts/Vazirmatn-Regular.ttf",
        alias="PDF_FONT_REGULAR_PATH",
    )
    pdf_font_bold_path: str = Field(
        default="./app/assets/fonts/Vazirmatn-Bold.ttf",
        alias="PDF_FONT_BOLD_PATH",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        alias="LOG_FORMAT",
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        alias="LOG_DATE_FORMAT",
    )

    voice_agent_url: str = Field(
        default="http://localhost:8000",
        alias="VOICE_AGENT_URL",
    )
    voice_agent_timeout_seconds: float = Field(
        default=5.0,
        alias="VOICE_AGENT_TIMEOUT_SECONDS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
