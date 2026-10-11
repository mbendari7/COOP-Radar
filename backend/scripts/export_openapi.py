"""Write the API's OpenAPI schema to frontend/openapi.json (the source for `npm run gen:api`).

Usage (from backend/): python -m scripts.export_openapi
CI runs this and fails if the committed schema or generated types are out of date.
"""

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost/unused")

from app.main import create_app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"

if __name__ == "__main__":
    schema = json.dumps(create_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:  # LF on every OS, so CI diffs cleanly
        f.write(schema + "\n")
    print(f"Wrote {OUT}")
