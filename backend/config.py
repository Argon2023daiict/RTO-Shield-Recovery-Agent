"""
Centralized configuration management using Pydantic Settings.
All secrets are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    database_url_sync: str = Field(..., alias="DATABASE_URL_SYNC")

    # LLM Configuration
    llm_provider: str = Field("groq", alias="LLM_PROVIDER")
    llm_model: str = Field("llama-3.3-70b-versatile", alias="LLM_MODEL")
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")

    # Razorpay
    razorpay_key_id: str = Field(..., alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str = Field(..., alias="RAZORPAY_KEY_SECRET")

    # Google Maps
    google_maps_api_key: Optional[str] = Field(None, alias="GOOGLE_MAPS_API_KEY")

    # Twilio / WhatsApp
    twilio_account_sid: Optional[str] = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(
        "whatsapp:+14155238886", alias="TWILIO_WHATSAPP_FROM"
    )

    # Application
    app_env: str = Field("development", alias="APP_ENV")
    app_secret_key: str = Field("supersecretkey123", alias="APP_SECRET_KEY")
    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")
    frontend_url: str = Field("http://localhost:8501", alias="FRONTEND_URL")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()