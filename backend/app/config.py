from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"
WORKSPACE_ENV_FILE = BACKEND_ROOT.parent / ".env"
ENV_FILE = BACKEND_ENV_FILE if BACKEND_ENV_FILE.exists() else WORKSPACE_ENV_FILE


class Settings(BaseSettings):
    database_url: SecretStr
    session_secret: SecretStr
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    session_cookie_secure: bool = False
    session_max_age_seconds: int = Field(default=28_800, ge=300, le=2_592_000)
    environment: Literal["development", "production", "test"] = "development"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins or any("*" in origin for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit origins and cannot include '*'")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS_ORIGINS entries must be HTTP or HTTPS origins")
        return ",".join(origins)

    @model_validator(mode="after")
    def require_secure_production_cookies(self) -> "Settings":
        if self.environment == "production" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true in production")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.get_secret_value()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
