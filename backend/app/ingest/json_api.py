"""JsonApiAdapter — fetches postings from a JSON API endpoint."""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting


def _read_local_json(url: str) -> Any:
    path = Path(unquote(urlparse(url).path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AdapterError(f"JsonApiAdapter could not read {url}: {exc}") from exc


class JsonApiAdapter(BaseAdapter):
    """
    Fetches postings from a JSON REST API.

    source.config must contain:
      - url: str            — the API endpoint URL
      - field_map: dict     — maps RawPosting field names to response keys
                              e.g. {"title": "job_title", "company": "employer"}
                              Fields not in the map fall back to the RawPosting field name.
    """

    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config
        url = config.get("url", "")
        field_map: dict[str, str] = config.get("field_map", {})

        if url.startswith("file://"):
            # Local fixture files (used by the dev seed sources) — httpx can't read file://
            data = await asyncio.to_thread(_read_local_json, url)
        else:
            transport = httpx.AsyncHTTPTransport(retries=3)
            async with httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": self.user_agent},
                transport=transport,
            ) as client:
                try:
                    response = await client.get(url)
                except httpx.HTTPError as exc:
                    raise AdapterError(f"JsonApiAdapter could not reach {url}: {exc}") from exc

            if response.status_code != 200:
                raise AdapterError(
                    f"JsonApiAdapter got HTTP {response.status_code} from {url}"
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise AdapterError(f"JsonApiAdapter got invalid JSON from {url}") from exc

        if not isinstance(data, list):
            # Support {"items": [...]} envelope
            data = data.get("items", data.get("postings", []))

        return [self._map(item, field_map) for item in data]

    def _map(self, item: dict[str, Any], field_map: dict[str, str]) -> RawPosting:
        def get(field: str) -> Any:
            key = field_map.get(field, field)
            return item.get(key)

        raw_deadline = get("deadline")
        parsed_deadline: date | None = None
        if isinstance(raw_deadline, str):
            try:
                parsed_deadline = date.fromisoformat(raw_deadline)
            except ValueError:
                parsed_deadline = None
        elif isinstance(raw_deadline, date):
            parsed_deadline = raw_deadline

        raw_skills = get("skills")
        skills: list[str] = []
        if isinstance(raw_skills, list):
            skills = [str(s) for s in raw_skills]
        elif isinstance(raw_skills, str):
            skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

        return RawPosting(
            title=str(get("title") or ""),
            company=str(get("company") or ""),
            city=str(get("city") or ""),
            term=str(get("term") or ""),
            work_mode=get("work_mode"),
            deadline=parsed_deadline,
            description=get("description"),
            skills=skills,
            source_ref=str(get("source_ref") or get("id") or ""),
            source_url=get("source_url"),
        )
