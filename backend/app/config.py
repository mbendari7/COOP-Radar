from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration comes from environment variables (or .env in dev).
    pydantic-settings will raise a clear error if a required var is missing,
    which beats cryptic runtime failures further down the stack.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # Comma-separated list of allowed CORS origins.
    # Example: "http://localhost:5173,https://coopradar.example.com"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    lru_cache means we parse the env exactly once per process,
    and tests can override by calling get_settings.cache_clear().
    """
    return Settings()
