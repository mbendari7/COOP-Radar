# Data Model: Browse & Search Postings

**Feature**: `001-browse-search-postings` | **Date**: 2026-10-09

---

## Entity: Posting

The central entity. One row per co-op job posting.

### Fields

| Column | Type | Nullable | Constraints | Notes |
|--------|------|----------|-------------|-------|
| `id` | UUID | No | PRIMARY KEY, default gen_random_uuid() | |
| `title` | TEXT | No | NOT NULL | Posting title |
| `company` | TEXT | No | NOT NULL | Company name |
| `city` | TEXT | No | NOT NULL | e.g. "Waterloo" |
| `province` | TEXT | No | NOT NULL | e.g. "ON" (2-char code) |
| `work_mode` | work_mode_enum | No | NOT NULL | onsite \| hybrid \| remote |
| `term` | TEXT | No | NOT NULL | e.g. "Summer 2027" |
| `duration_months` | SMALLINT | No | NOT NULL, CHECK IN (4,8,12,16) | |
| `deadline` | DATE | No | NOT NULL | Application deadline |
| `posted_at` | TIMESTAMPTZ | No | NOT NULL, default NOW() | |
| `description` | TEXT | No | NOT NULL | Full posting description |
| `source_url` | TEXT | Yes | | URL to original posting; NULL if unavailable |
| `skills` | TEXT[] | No | NOT NULL, default '{}' | Required skills list |
| `search_vector` | TSVECTOR | Yes | GENERATED ALWAYS AS (…) STORED | Auto-updated from title, company, skills, description |

### Enum: work_mode

```sql
CREATE TYPE work_mode_enum AS ENUM ('onsite', 'hybrid', 'remote');
```

### Computed / Derived

- **`is_active`**: Derived at query time as `deadline >= CURRENT_DATE`; not stored as a column.
  The `show_expired` toggle adds or removes this filter predicate.

### Indexes

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_postings_search_vector` | GIN | `search_vector` | Full-text keyword search (`@@`) |
| `idx_postings_skills` | GIN | `skills` | Skills contains-all filter (`@>`) |
| `idx_postings_posted_at` | B-tree | `posted_at DESC` | Default sort; deadline for newest-first |
| `idx_postings_deadline` | B-tree | `deadline` | Sort by deadline; active filter |
| `idx_postings_company` | B-tree | `company` | Sort by company |
| `idx_postings_title` | B-tree | `title` | Sort by title |
| `idx_postings_city` | B-tree | `city` | City filter |
| `idx_postings_province` | B-tree | `province` | Province filter |
| `idx_postings_term` | B-tree | `term` | Term filter |
| `idx_postings_work_mode` | B-tree | `work_mode` | Work-mode filter |
| `idx_postings_duration` | B-tree | `duration_months` | Duration filter |

### `search_vector` generation expression

```sql
to_tsvector('english',
  setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
  setweight(to_tsvector('english', array_to_string(skills, ' ')), 'B') ||
  setweight(to_tsvector('english', coalesce(description, '')), 'C')
)
```

Weight A (title) > Weight B (company, skills) > Weight C (description), fulfilling FR-003.

---

## SQLAlchemy Model (reference)

```python
# backend/app/models/posting.py
import enum
from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import (
    CheckConstraint, Column, Date, Enum, Index, SmallInteger,
    String, Text, TIMESTAMP, text, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

class WorkMode(str, enum.Enum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"

class Posting(Base):
    __tablename__ = "postings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str] = mapped_column(String(2), nullable=False)
    work_mode: Mapped[WorkMode] = mapped_column(Enum(WorkMode), nullable=False)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    duration_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        CheckConstraint("duration_months IN (4, 8, 12, 16)", name="ck_duration_months"),
        Index("idx_postings_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_postings_skills", "skills", postgresql_using="gin"),
        Index("idx_postings_posted_at", "posted_at"),
        Index("idx_postings_deadline", "deadline"),
        Index("idx_postings_company", "company"),
        Index("idx_postings_title", "title"),
        Index("idx_postings_city", "city"),
        Index("idx_postings_province", "province"),
        Index("idx_postings_term", "term"),
        Index("idx_postings_work_mode", "work_mode"),
        Index("idx_postings_duration", "duration_months"),
    )
```

---

## Seed Data Shape

~60 rows covering:
- Cities: Toronto, Mississauga, Waterloo, Kitchener, Guelph, Hamilton, Ottawa, Vancouver + a handful with `work_mode=remote`
- Terms: Winter 2027 (≈20), Summer 2027 (≈25), Fall 2027 (≈15)
- Durations: mix of 4, 8, 12, 16 months
- Skills: ~20–30 distinct skills from the fixed taxonomy (Python, Java, React, TypeScript, SQL, C++, Go, AWS, Docker, etc.)
- Deadlines: mix of future (active) and past (expired) dates
