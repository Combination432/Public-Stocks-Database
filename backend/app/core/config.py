"""
Configuration management for the US Financial Statement Database API.
Uses pydantic-settings for environment variable management.
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/financial_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    VALID_API_KEYS: str = "demo-key-12345"

    # SEC EDGAR Configuration
    SEC_USER_AGENT: str = "Financial Database App contact@example.com"
    SEC_RATE_LIMIT_DELAY: float = 0.1  # seconds between requests

    # ETL Configuration
    ETL_BATCH_SIZE: int = 10
    ETL_BACKFILL_YEARS: int = 10
    ETL_CHECK_INTERVAL: int = 3600  # seconds (1 hour)

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("VALID_API_KEYS")
    @classmethod
    def parse_api_keys(cls, v: str) -> List[str]:
        """Parse comma-separated API keys into a list."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def api_keys_list(self) -> List[str]:
        """Get list of valid API keys."""
        if isinstance(self.VALID_API_KEYS, str):
            return [key.strip() for key in self.VALID_API_KEYS.split(",")]
        return self.VALID_API_KEYS


# Global settings instance
settings = Settings()
