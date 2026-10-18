from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    APP_ENV: str = Field(default="development", description="Environment: development, staging, production")
    APP_DEBUG: bool = Field(default=True, description="Enable debug mode")
    APP_NAME: str = Field(default="Forging CMS", description="Application Title")
    APP_VERSION: str = Field(default="1.0.0", description="Application Version")
    SECRET_KEY: str = Field(
        default="development_insecure_secret_key_please_replace_in_env_file_32chars",
        description="Cryptographic secret key for signing cookies and tokens",
    )
    SITE_URL: str = Field(default="http://localhost:8000", description="Public Base URL")

    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./forging.db",
        description="Database connection URL (SQLite or MySQL)",
    )

    # File Upload Settings
    UPLOAD_DIR: str = Field(default="./uploads", description="Directory to store uploaded media")
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, description="Maximum upload size in bytes (10MB default)")

    # Session & Cookie Security
    SESSION_COOKIE_NAME: str = Field(default="forging_admin_session", description="Admin session cookie name")
    SESSION_MAX_AGE_SECONDS: int = Field(default=86400, description="Session lifetime in seconds (24h default)")
    SESSION_COOKIE_SECURE: bool = Field(default=False, description="Require HTTPS for cookie")
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True, description="Prevent JS access to cookie")
    SESSION_COOKIE_SAMESITE: str = Field(default="lax", description="SameSite policy: lax, strict, none")

    # Super Admin Bootstrap Settings
    FIRST_SUPERADMIN_EMAIL: str = Field(default="admin@forgingcms.com", description="Bootstrap Super Admin Email")
    FIRST_SUPERADMIN_PASSWORD: str = Field(default="Admin@123456", description="Bootstrap Super Admin Password")
    FIRST_SUPERADMIN_NAME: str = Field(default="System Super Admin", description="Bootstrap Super Admin Name")

    # Mail Settings Placeholders
    MAIL_SERVER: str = Field(default="smtp.example.com", description="SMTP server host")
    MAIL_PORT: int = Field(default=587, description="SMTP server port")
    MAIL_USERNAME: str = Field(default="", description="SMTP username")
    MAIL_PASSWORD: str = Field(default="", description="SMTP password")
    MAIL_FROM: str = Field(default="no-reply@forgingcms.com", description="Default sender email")
    MAIL_TLS: bool = Field(default=True, description="Use STARTTLS")
    MAIL_SSL: bool = Field(default=False, description="Use SSL")

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def resolved_upload_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            return BASE_DIR / p
        return p


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
