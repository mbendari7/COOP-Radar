# API Contracts: Browse & Search Postings

**Feature**: `001-browse-search-postings` | **Date**: 2026-10-09

Base URL: `http://localhost:8000` (dev) | `/api` prefix on all routes

---

## GET /api/postings

Returns a paginated, filtered, sorted list of co-op postings.

### Query Parameters

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `q` | string | — | max 200 chars | Keyword search across title, company, skills, description |
| `city` | string | — | | Filter by city (exact match, case-insensitive) |
| `province` | string | — | 2-char code | Filter by province (e.g. `ON`, `BC`) |
| `term` | string | — | | Filter by term label (e.g. `Summer 2027`) |
| `work_mode` | string | — | `onsite\|hybrid\|remote` | Filter by work mode |
| `duration` | int[] | — | values in {4,8,12,16} | One or more duration values; OR'd |
| `skills` | string[] | — | | One or more skill names; AND'd (posting must have ALL) |
| `show_expired` | boolean | `false` | | If false, hides postings with `deadline < today` |
| `sort` | string | `posted_at` | `posted_at\|deadline\|company\|title` | Sort column |
| `order` | string | `desc` | `asc\|desc` | Sort direction |
| `page` | integer | `1` | ≥ 1 | 1-based page number |
| `page_size` | integer | `25` | `10\|25\|50` | Results per page |

### Response 200 OK

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Backend Developer Co-op",
      "company": "Shopify",
      "city": "Ottawa",
      "province": "ON",
      "work_mode": "hybrid",
      "term": "Summer 2027",
      "duration_months": 4,
      "deadline": "2027-02-28",
      "posted_at": "2026-09-15T10:00:00Z",
      "skills": ["Python", "Django", "PostgreSQL"],
      "source_url": "https://example.com/job/123"
    }
  ],
  "total": 14,
  "page": 1,
  "page_size": 25
}
```

**Note**: The list response omits `description` and `search_vector` to keep payloads small.

### Response 422 Unprocessable Entity

```json
{
  "detail": "Invalid sort column: 'foo'",
  "code": "INVALID_SORT_COLUMN"
}
```

Returned when:
- `sort` is not in the allowed whitelist
- `order` is not `asc` or `desc`
- `page_size` is not 10, 25, or 50
- `duration` contains values not in {4, 8, 12, 16}
- `work_mode` is not a recognised enum value

---

## GET /api/postings/{id}

Returns full detail for a single posting.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Posting identifier |

### Response 200 OK

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Backend Developer Co-op",
  "company": "Shopify",
  "city": "Ottawa",
  "province": "ON",
  "work_mode": "hybrid",
  "term": "Summer 2027",
  "duration_months": 4,
  "deadline": "2027-02-28",
  "posted_at": "2026-09-15T10:00:00Z",
  "description": "Full job description text here...",
  "skills": ["Python", "Django", "PostgreSQL"],
  "source_url": "https://example.com/job/123"
}
```

### Response 404 Not Found

```json
{
  "detail": "Posting not found",
  "code": "POSTING_NOT_FOUND"
}
```

---

## GET /api/postings/meta/filters

Returns all distinct values available for filter dropdowns.
Used by the frontend to populate city, province, term, and skills filter options.

### Response 200 OK

```json
{
  "cities": ["Guelph", "Hamilton", "Kitchener", "Mississauga", "Ottawa", "Toronto", "Vancouver", "Waterloo"],
  "provinces": ["BC", "ON"],
  "terms": ["Fall 2027", "Summer 2027", "Winter 2027"],
  "skills": ["AWS", "C++", "Docker", "Go", "Java", "PostgreSQL", "Python", "React", "SQL", "TypeScript"]
}
```

Values are sorted alphabetically. Only values present in the `postings` table are returned.

---

## Pydantic Schemas (reference)

```python
# backend/app/schemas/posting.py

class PostingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str
    city: str
    province: str
    work_mode: WorkMode
    term: str
    duration_months: int
    deadline: date
    posted_at: datetime
    skills: list[str]
    source_url: str | None

class PostingDetail(PostingListItem):
    description: str

class PostingsPage(BaseModel):
    items: list[PostingListItem]
    total: int
    page: int
    page_size: int

class FilterMeta(BaseModel):
    cities: list[str]
    provinces: list[str]
    terms: list[str]
    skills: list[str]

class PostingListParams(BaseModel):
    q: str | None = None
    city: str | None = None
    province: str | None = None
    term: str | None = None
    work_mode: WorkMode | None = None
    duration: list[int] | None = None
    skills: list[str] | None = None
    show_expired: bool = False
    sort: Literal["posted_at", "deadline", "company", "title"] = "posted_at"
    order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    page_size: Literal[10, 25, 50] = 25
```
