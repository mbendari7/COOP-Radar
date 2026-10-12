---
name: db-migration
description: Create and apply an Alembic migration for a CoopRadar schema change, safely.
disable-model-invocation: true
argument-hint: "[what changed]"
---

Create a migration for: $ARGUMENTS

1. Update the SQLAlchemy models first. Declare every index in the model's `__table_args__` (including DESC,
   GIN, and HNSW indexes) — anything that exists only in a migration will be dropped by the next autogenerate.
2. Generate (in `backend/`, venv active): `alembic revision --autogenerate -m "$ARGUMENTS"`.
   Name the file with the next number after the newest in `backend/alembic/versions/` (e.g. `0010_<slug>.py`,
   `revision = "0010"`, `down_revision = "0009"`) to match the existing style.
3. Review the generated file by hand:
   - indexes present; nothing dropped by accident; enums created with `checkfirst=True`
   - pgvector columns are `vector(1536)` with an HNSW `vector_cosine_ops` index
   - generated columns only call IMMUTABLE functions (e.g. use `coopradar_skills_text()`, not `array_to_string()`)
   - extensions via `op.execute("CREATE EXTENSION IF NOT EXISTS ...")`
   - `downgrade()` truly reverses `upgrade()`
4. Prove it round-trips:
   `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
5. Prove models and migrations agree: `alembic check` must print "No new upgrade operations detected."
6. Run `pytest -q`. Report the migration file name and any manual edits you made.

Never edit a migration that has already been applied to a shared database — add a new one instead.
