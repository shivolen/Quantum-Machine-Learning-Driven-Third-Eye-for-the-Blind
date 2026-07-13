from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables (or .env file).

    Environment variable names are automatically inferred from field names (uppercase),
    or explicitly set via Field(env="VAR_NAME").
    """

    # Server configuration
    PORT: int = 8000

    # Gemini API configuration
    GEMINI_API_KEY: str = "AIzaSyDHrDQO1lbxPbcGvfotV8_6L7y8QASiRvw"
    GEMINI_MODEL: str = "gemini-2.5-flash-lite" 
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

    # Vision analysis settings
    FRAME_CAPTURE_INTERVAL: float = 3.0  # seconds between frame captures
    DEBUG_MODE: bool = False  # Enable debug logging

    # ESP32-CAM configuration
    esp32_ip: str | None = Field(default=None, env="ESP32_IP")
    backend_endpoint: str = Field(
        default="http://127.0.0.1:8000/detect_objects",
        env="BACKEND_ENDPOINT",
    )
    send_interval: int = Field(default=3, env="SEND_INTERVAL")
    use_esp32: bool = Field(default=False, env="USE_ESP32")

    # Pydantic v2 settings: ignore extra env vars to prevent validation errors
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
