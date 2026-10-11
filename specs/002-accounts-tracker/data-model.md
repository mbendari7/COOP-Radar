# Data Model: Accounts & Application Tracker

**Feature**: `002-accounts-tracker` | **Date**: 2026-10-10

---

## Entity: User

One row per registered student.

### Fields

| Column | Type | Nullable | Constraints | Notes |
|--------|------|----------|-------------|-------|
| `id` | UUID | No | PRIMARY KEY, default gen_random_uuid() | |
| `email` | TEXT | No | NOT NULL, UNIQUE | Stored lowercase |
| `hashed_password` | TEXT | No | NOT NULL | argon2id hash |
| `created_at` | TIMESTAMPTZ | No | NOT NULL, default NOW() | |

### Indexes

| Index | Type | Column | Purpose |
|-------|------|--------|---------|
| `idx_users_email` | B-tree UNIQUE | `email` | Login lookup; enforces uniqueness |

### SQLAlchemy model (reference)

```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    saved_postings: Mapped[list["SavedPosting"]] = relationship(back_populates="user")
```

---

## Entity: SavedPosting

One row per (user, posting) bookmark. Each user can save a posting at most once.

### Fields

| Column | Type | Nullable | Constraints | Notes |
|--------|------|----------|-------------|-------|
| `id` | UUID | No | PRIMARY KEY | |
| `user_id` | UUID | No | NOT NULL, FK → users.id ON DELETE CASCADE | |
| `posting_id` | UUID | No | NOT NULL, FK → postings.id ON DELETE CASCADE | |
| `status` | application_status_enum | Yes | NULL = no status set | `applied` / `interviewing` / `offer` / `rejected` |
| `saved_at` | TIMESTAMPTZ | No | NOT NULL, default NOW() | Used for default sort |

### Enum: application_status

```sql
CREATE TYPE application_status_enum AS ENUM ('applied', 'interviewing', 'offer', 'rejected');
```

### Constraints

```sql
UNIQUE (user_id, posting_id)   -- one save per (user, posting)
```

`ON DELETE CASCADE` on both FKs means:
- Deleting a user automatically removes all their saved postings (FR-013).
- Deleting a posting removes it from all saved lists (future-proofing for ingestion cleanup).

### Indexes

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_saved_postings_user_id` | B-tree | `user_id` | List a user's saved postings |
| `idx_saved_postings_posting_id` | B-tree | `posting_id` | Check if a posting is saved |
| `ux_saved_postings_user_posting` | B-tree UNIQUE | `(user_id, posting_id)` | Enforce one save per pair; idempotent upsert |
| `idx_saved_postings_status` | B-tree | `status` | Filter by status on the Saved page |
| `idx_saved_postings_saved_at` | B-tree | `saved_at DESC` | Default sort (most recently saved) |

### SQLAlchemy model (reference)

```python
# backend/app/models/saved_posting.py
class ApplicationStatus(str, enum.Enum):
    applied      = "applied"
    interviewing = "interviewing"
    offer        = "offer"
    rejected     = "rejected"

class SavedPosting(Base):
    __tablename__ = "saved_postings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    posting_id: Mapped[UUID] = mapped_column(ForeignKey("postings.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[ApplicationStatus | None] = mapped_column(
        Enum(ApplicationStatus, name="application_status_enum"), nullable=True
    )
    saved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    user: Mapped["User"] = relationship(back_populates="saved_postings")
    posting: Mapped["Posting"] = relationship()
```

---

## Redis Session Schema

Not a relational table — stored in Redis as a hash.

| Key pattern | Type | Fields | TTL |
|------------|------|--------|-----|
| `session:<32-byte-hex-token>` | Redis HASH | `user_id=<uuid>` | 7 days, rolling |

The token is generated with `secrets.token_hex(32)` (256 bits of entropy).
The TTL is reset on every successful authenticated request.

---

## Migration: 0002_add_auth

One Alembic migration handles both new tables and the Redis schema is implicit
(no migration needed for Redis).

```
upgrade():
  CREATE TYPE application_status_enum AS ENUM (...)
  CREATE TABLE users (...)
  CREATE TABLE saved_postings (...)
  CREATE all indexes

downgrade():
  DROP TABLE saved_postings
  DROP TABLE users
  DROP TYPE application_status_enum
```
