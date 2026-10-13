"""Tests for JsonApiAdapter with respx faking the replies, so nothing goes over the network."""

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.ingest.base import AdapterError
from app.ingest.json_api import JsonApiAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ingest"


def make_source(url: str, field_map: dict | None = None):
    """Makes a small object that looks enough like an IngestSource."""

    class FakeSource:
        config = {"url": url, "field_map": field_map or {}}

    return FakeSource()


@pytest.mark.asyncio
async def test_happy_path_returns_raw_postings():
    """The normal case. 5 raw jobs come back matching the acme_jobs.json file."""
    fixture_data = json.loads((FIXTURE_DIR / "acme_jobs.json").read_text())

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://acme.example.com/jobs").mock(
            return_value=Response(200, json=fixture_data)
        )
        adapter = JsonApiAdapter()
        source = make_source("https://acme.example.com/jobs")
        postings = await adapter.fetch(source)

    assert len(postings) == 5
    assert postings[0].title == "Backend Software Developer Co-op"
    assert postings[0].company == "Acme Corp"
    assert postings[0].city == "Waterloo"
    assert postings[0].source_ref == "acme-001"
    assert "Python" in postings[0].skills


@pytest.mark.asyncio
async def test_http_500_raises_adapter_error():
    """A reply that is not 200 raises AdapterError."""
    with respx.mock() as mock:
        mock.get("https://broken.example.com/jobs").mock(
            return_value=Response(500)
        )
        adapter = JsonApiAdapter()
        source = make_source("https://broken.example.com/jobs")

        with pytest.raises(AdapterError, match="HTTP 500"):
            await adapter.fetch(source)


@pytest.mark.asyncio
async def test_empty_array_returns_empty_list():
    """An empty list reply gives an empty list and no error."""
    with respx.mock() as mock:
        mock.get("https://empty.example.com/jobs").mock(
            return_value=Response(200, json=[])
        )
        adapter = JsonApiAdapter()
        source = make_source("https://empty.example.com/jobs")
        postings = await adapter.fetch(source)

    assert postings == []


@pytest.mark.asyncio
async def test_field_map_remapping():
    """A custom field_map maps reply keys onto RawPosting fields."""
    data = [
        {
            "job_title": "QA Engineer Co-op",
            "employer": "TestCo",
            "location": "Ottawa",
            "period": "Fall 2027",
            "due_date": "2027-06-15",
        }
    ]
    field_map = {
        "title": "job_title",
        "company": "employer",
        "city": "location",
        "term": "period",
        "deadline": "due_date",
    }
    with respx.mock() as mock:
        mock.get("https://mapped.example.com/jobs").mock(
            return_value=Response(200, json=data)
        )
        adapter = JsonApiAdapter()
        source = make_source("https://mapped.example.com/jobs", field_map=field_map)
        postings = await adapter.fetch(source)

    assert len(postings) == 1
    assert postings[0].title == "QA Engineer Co-op"
    assert postings[0].company == "TestCo"
    assert postings[0].city == "Ottawa"
