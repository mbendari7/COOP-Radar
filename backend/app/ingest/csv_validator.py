"""CSV upload validation helpers."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class RowError:
    row: int
    column: str
    message: str


@dataclass
class CsvUploadResult:
    added: int
    skipped_duplicates: int
    errors: list[RowError] = field(default_factory=list)


_REQUIRED_COLUMNS = {"title", "company", "city", "term", "deadline"}
_VALID_WORK_MODES = {"onsite", "hybrid", "remote"}


def validate_csv_row(row: dict[str, Any], row_num: int) -> list[RowError]:
    """
    Validate a single CSV row (as a dict from pandas).
    Returns a list of RowErrors; empty list means the row is valid.
    """
    errors: list[RowError] = []

    for col in _REQUIRED_COLUMNS:
        val = row.get(col)
        if val is None or str(val).strip() == "" or str(val).lower() == "nan":
            errors.append(
                RowError(
                    row=row_num, column=col, message=f"Required field '{col}' is missing or empty."
                )
            )

    # Validate deadline format (only if the column was present)
    deadline_val = row.get("deadline")
    if deadline_val and str(deadline_val).strip() and str(deadline_val).lower() != "nan":
        try:
            date.fromisoformat(str(deadline_val).strip())
        except ValueError:
            errors.append(
                RowError(
                    row=row_num,
                    column="deadline",
                    message="Invalid date format. Expected YYYY-MM-DD.",
                )
            )

    # Validate optional work_mode if present
    work_mode_val = row.get("work_mode")
    work_mode = str(work_mode_val or "").strip().lower()
    if work_mode and work_mode != "nan" and work_mode not in _VALID_WORK_MODES:
        allowed = ", ".join(sorted(_VALID_WORK_MODES))
        errors.append(
            RowError(
                row=row_num,
                column="work_mode",
                message=f"Invalid work_mode. Must be one of: {allowed}.",
            )
        )

    return errors
