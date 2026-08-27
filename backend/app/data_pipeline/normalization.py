"""Shared parsing and validation helpers for source rows."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.data_pipeline.errors import DataNormalizationError

_MISSING = object()


def first_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = row.get(name, _MISSING)
        if value is not _MISSING and value is not None and str(value).strip() != "":
            return value
    return default


def parse_number(value: Any, *, field: str) -> float | int | str | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        raise DataNormalizationError(f"{field} must be numeric")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise DataNormalizationError(f"{field} must be finite")
        return value
    text = str(value).strip()
    if text.casefold() in {"not_detected", "not detected", "nd", "na", "n/a"}:
        return text
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return text
    if not math.isfinite(number):
        raise DataNormalizationError(f"{field} must be finite")
    return int(number) if number.is_integer() else number


def parse_coordinate(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    parsed = parse_number(value, field=field)
    if not isinstance(parsed, (int, float)) or isinstance(parsed, bool):
        raise DataNormalizationError(f"{field} is required and must be numeric")
    numeric = float(parsed)
    if not minimum <= numeric <= maximum:
        raise DataNormalizationError(f"{field} is outside [{minimum}, {maximum}]")
    return numeric


def parse_datetime(value: Any, *, field: str = "observed_at") -> datetime:
    if value is None or str(value).strip() == "":
        raise DataNormalizationError(f"{field} is required")
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            result = datetime.fromisoformat(text)
        except ValueError as error:
            raise DataNormalizationError(f"invalid {field}: {value!r}") from error
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)
