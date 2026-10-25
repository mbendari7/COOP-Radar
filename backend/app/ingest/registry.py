"""Maps each adapter_type name to its adapter class."""

from app.ingest.adzuna import AdzunaAdapter
from app.ingest.ats import BambooHrAdapter, RecruiteeAdapter, RipplingAdapter
from app.ingest.base import BaseAdapter
from app.ingest.boards import (
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
)
from app.ingest.github_lists import GithubListAdapter
from app.ingest.himalayas import HimalayasAdapter
from app.ingest.json_api import JsonApiAdapter
from app.ingest.oracle import OracleAdapter
from app.ingest.rss import RssAdapter
from app.ingest.simplify import SimplifyAdapter
from app.ingest.themuse import TheMuseAdapter
from app.ingest.workable import WorkableAdapter
from app.ingest.workday import WorkdayAdapter

_ADAPTERS: dict[str, type[BaseAdapter]] = {
    "json_api": JsonApiAdapter,
    "rss": RssAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
    "workday": WorkdayAdapter,
    "adzuna": AdzunaAdapter,
    "workable": WorkableAdapter,
    "simplify": SimplifyAdapter,
    "recruitee": RecruiteeAdapter,
    "bamboohr": BambooHrAdapter,
    "rippling": RipplingAdapter,
    "github_list": GithubListAdapter,
    "oracle": OracleAdapter,
    "themuse": TheMuseAdapter,
    "himalayas": HimalayasAdapter,
}


def adapter_for(source: object) -> BaseAdapter:
    """
    Gives back the right adapter for this source.

    Raises ValueError for an adapter_type we do not know.
    """
    adapter_type = getattr(source, "adapter_type", "")
    if adapter_type not in _ADAPTERS:
        raise ValueError(f"Unknown adapter_type: {adapter_type!r}")
    return _ADAPTERS[adapter_type]()
