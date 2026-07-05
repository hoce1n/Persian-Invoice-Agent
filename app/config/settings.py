from functools import lru_cache

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
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    debug: bool = True

    bynara_api_key: str = ""
    bynara_base_url: str = "https://router.bynara.id/v1"
    bynara_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"

    email_service_api_key: str = ""
    email_from_address: str = "invoices@example.com"
    email_approval_recipient: str = "approver@example.com"
    manager_email: str = "manager@example.com"
    default_client_email: str = "client@example.com"

    pdf_output_dir: str = "./generated_invoices"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
