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

    # Session cookies are marked Secure by default. Browsers treat http://localhost as a
    # secure context, so this works in local dev; the test suite sets it to false because
    # httpx (like any non-browser client) won't send Secure cookies over plain http.
    cookie_secure: bool = True

    # --- AI providers -------------------------------------------------------
    # Empty keys are allowed so the app still boots without AI features configured;
    # the AI endpoints degrade gracefully (see services/resume.py and ingest/extract.py).
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model for the resume Q&A assistant (quality matters most here).
    agent_model: str = "claude-opus-5-5"
    # Model for high-volume structured calls: match re-ranking and field extraction.
    fast_model: str = "claude-haiku-5-5"
    # OpenAI embedding model. Must produce 1536-dim vectors to fit posting_embeddings.
    embed_model: str = "text-embedding-3-small"

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
