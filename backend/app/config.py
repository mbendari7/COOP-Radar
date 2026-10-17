import re
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canada, the provinces, big Canadian cities and Remote Canada
CANADA_LOCATION_FILTER = (
    r"canada|toronto|waterloo|kitchener|ottawa|vancouver|montr[eé]al|calgary|edmonton|"
    r"guelph|hamilton|mississauga|markham|burnaby|halifax|winnipeg|qu[eé]bec|regina|"
    r"saskatoon|victoria, bc|london, on|ontario|british columbia|alberta|nova scotia|"
    r"(?-i:\b(?:ON|BC|AB|QC|MB|SK|NS|NB|NL|PE)\b)"
)


class Settings(BaseSettings):
    """
    Every setting comes from environment variables or from .env on your own computer.
    If something required is missing pydantic tells you right away
    which is a lot nicer than a strange crash later.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Optional. Leave it empty and sessions and counters live in Postgres (app/store.py)
    # so the site only needs a database. Set a redis:// URL to keep them in Redis instead
    redis_url: str = ""
    # Import career boards in the background inside the web server (app/jobs.py)
    background_jobs: bool = True

    # Comma separated list of sites allowed to call the API
    # Example "http://localhost:5173,https://coopradar.example.com"
    cors_origins: str = "http://localhost:5173"

    # Session cookies are Secure by default. Browsers treat http://localhost as secure so this
    # still works on your own computer. Tests turn it off because httpx will not send
    # Secure cookies over plain http
    cookie_secure: bool = True

    # AI providers are all optional
    # Visitors usually bring their own Claude, ChatGPT or Gemini key (see app/ai.py) so the
    # owner pays nothing. Setting ANTHROPIC_API_KEY lets people without a key use AI too
    # up to ai_daily_limit. OPENAI_API_KEY turns on smart search
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model for the resume Q and A helper where quality matters most
    agent_model: str = "claude-opus-5-5"
    # Model for the many small calls like reranking matches and pulling out fields
    fast_model: str = "claude-haiku-5-5"
    # OpenAI embedding model. It has to make 1536 number vectors to fit posting_embeddings
    embed_model: str = "text-embedding-3-small"

    # Public hosting
    # Try the demo accounts (see app/services/demo.py)
    demo_enabled: bool = True
    # AI actions like resume uploads and questions per person per UTC day. 0 means no limit
    ai_daily_limit: int = 20
    # Folder with the built React site. When it exists the API serves the website too
    # so one process is the whole site. start.py points it at frontend/dist
    static_dir: str = ""
    # Postgres stops any single query that runs longer than this many milliseconds
    db_statement_timeout_ms: int = 10_000

    # Imports only keep jobs whose location matches this regex. Case does not matter except
    # for province codes. Leave it empty for the Canada default below
    # Use ".*" to keep every location
    ingest_location_filter: str = CANADA_LOCATION_FILTER
    # Jobs in the US. "students" keeps roles open to students and recent grads, like co-op,
    # intern, new grad, junior and entry level (EARLY_CAREER_TITLE in app/ingest/boards.py),
    # since lots of Canadian students do a US term. "all" keeps every US job, which can be tens
    # of thousands and fills a free database fast. "none" skips them. Every job in Canada is
    # always kept
    ingest_us_jobs: Literal["students", "all", "none"] = "students"
    # Optional Adzuna job search API keys (app/ingest/adzuna.py), a paid plan at
    # developer.adzuna.com.
    # With both set we also import student jobs Adzuna gathers from employer sites in every field
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    @field_validator("ingest_location_filter")
    @classmethod
    def _default_location_filter(cls, v: str) -> str:
        return v.strip() or CANADA_LOCATION_FILTER

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, v: str) -> str:
        """
        Accept the database URLs hosts hand out like postgres:// or postgresql:// or
        ?sslmode=require and turn them into what SQLAlchemy and asyncpg want. Neon adds
        &channel_binding=require which asyncpg does not accept so we drop it.
        """
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                v = "postgresql+asyncpg://" + v[len(prefix):]
        v = re.sub(r"[?&]channel_binding=[^&]*", "", v)
        if "?" not in v and "&" in v:  # the one we dropped was the first parameter
            v = v.replace("&", "?", 1)
        return v.replace("sslmode=", "ssl=")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Give back one shared Settings object.
    lru_cache means we read the env once per process
    and tests can reset it with get_settings.cache_clear().
    """
    return Settings()
