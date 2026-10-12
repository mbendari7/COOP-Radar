import re
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canada, Canadian provinces and major cities, and "Remote - Canada"
CANADA_LOCATION_FILTER = (
    r"canada|toronto|waterloo|kitchener|ottawa|vancouver|montr[eé]al|calgary|edmonton|"
    r"guelph|hamilton|mississauga|markham|burnaby|halifax|winnipeg|qu[eé]bec|regina|"
    r"saskatoon|victoria, bc|london, on|ontario|british columbia|alberta|nova scotia|"
    r"(?-i:\b(?:ON|BC|AB|QC|MB|SK|NS|NB|NL|PE)\b)"
)


class Settings(BaseSettings):
    """
    All configuration comes from environment variables (or .env in dev).
    pydantic-settings will raise a clear error if a required var is missing,
    which beats cryptic runtime failures further down the stack.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Optional. Empty = sessions and counters live in Postgres (app/store.py), so the site
    # needs nothing but a database. Set it (redis://...) to use Redis for them instead.
    redis_url: str = ""
    # Run career-board imports in the background inside the web server (app/jobs.py).
    background_jobs: bool = True

    # Comma-separated list of allowed CORS origins.
    # Example: "http://localhost:5173,https://coopradar.example.com"
    cors_origins: str = "http://localhost:5173"

    # Session cookies are marked Secure by default. Browsers treat http://localhost as a
    # secure context, so this works in local dev; the test suite sets it to false because
    # httpx (like any non-browser client) won't send Secure cookies over plain http.
    cookie_secure: bool = True

    # --- AI providers (all optional) ------------------------------------------
    # Visitors normally bring their OWN key (Claude, ChatGPT, or Gemini — see app/ai.py), so
    # the site owner pays nothing. Setting ANTHROPIC_API_KEY here lets visitors without a key
    # use AI too (limited by ai_daily_limit). OPENAI_API_KEY enables smart search.
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model for the resume Q&A assistant (quality matters most here).
    agent_model: str = "claude-opus-5-5"
    # Model for high-volume structured calls: match re-ranking and field extraction.
    fast_model: str = "claude-haiku-5-5"
    # OpenAI embedding model. Must produce 1536-dim vectors to fit posting_embeddings.
    embed_model: str = "text-embedding-3-small"

    # --- Public hosting -------------------------------------------------------
    # One-click "Try the demo" accounts (see app/services/demo.py).
    demo_enabled: bool = True
    # AI actions (resume uploads + Q&A questions) per user per UTC day; 0 = unlimited.
    ai_daily_limit: int = 20
    # Folder with the built React app (index.html + assets/). When it exists, the API also
    # serves the website, so one process = the whole site. start.py sets it to frontend/dist.
    static_dir: str = ""
    # Postgres cancels any single statement that runs longer than this (milliseconds).
    db_statement_timeout_ms: int = 10_000

    # Career-board imports keep only jobs whose location matches this regex (case-insensitive;
    # province codes are matched case-sensitively). Empty = the Canada default below.
    # Set to ".*" to keep every location.
    ingest_location_filter: str = CANADA_LOCATION_FILTER
    # Jobs in the United States: "students" keeps only co-op / intern / student / new-grad roles
    # (many Canadian students do a US co-op term), "all" keeps every US job, "none" skips them.
    ingest_us_jobs: Literal["students", "all", "none"] = "students"

    @field_validator("ingest_location_filter")
    @classmethod
    def _default_location_filter(cls, v: str) -> str:
        return v.strip() or CANADA_LOCATION_FILTER

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, v: str) -> str:
        """
        Accept the URL formats hosting providers hand out (postgres://, postgresql://,
        ?sslmode=require) and convert them to what SQLAlchemy + asyncpg expect. Neon adds
        &channel_binding=require, which asyncpg doesn't accept, so it's dropped.
        """
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                v = "postgresql+asyncpg://" + v[len(prefix):]
        v = re.sub(r"[?&]channel_binding=[^&]*", "", v)
        if "?" not in v and "&" in v:  # the dropped parameter was the first one
            v = v.replace("&", "?", 1)
        return v.replace("sslmode=", "ssl=")

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
