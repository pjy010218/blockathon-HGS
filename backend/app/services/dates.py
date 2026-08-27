from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

_CLOCK_RANGE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)-(\d{2}:\d{2}(?::\d{2})?)$"
)


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO timestamp, including EMS clock ranges like 10:30-10:35."""
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        match = _CLOCK_RANGE.fullmatch(text)
        if match is None:
            raise
        return datetime.fromisoformat(match.group(1))

    offset = parsed.utcoffset()
    if offset is not None and int(offset.total_seconds()) % (15 * 60) != 0:
        match = _CLOCK_RANGE.fullmatch(text)
        if match is not None:
            return datetime.fromisoformat(match.group(1))
    return parsed


def parse_observed_at(payload: Mapping[str, Any]) -> datetime:
    lowered = {str(key).strip().lower(): value for key, value in payload.items()}
    for key in ("observed_at", "datetime", "observed_date_time"):
        raw = lowered.get(key)
        if raw in (None, ""):
            continue
        if isinstance(raw, datetime):
            return raw
        return parse_iso_datetime(str(raw))

    date = lowered.get("date")
    if not date:
        raise ValueError("A community row needs observed_at.")
    time = str(lowered.get("time") or "00:00")
    tz = str(lowered.get("timezone") or "+00:00")
    if time.count(":") == 1:
        time = f"{time}:00"
    return parse_iso_datetime(f"{date}T{time}{tz}")


def _replace_year(moment: datetime, year: int) -> datetime:
    try:
        return moment.replace(year=year)
    except ValueError:
        return moment.replace(year=year, day=28)


def _comparable(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def series_offset_to_end_year(
    moments: Iterable[datetime], end_year: int = 2025
) -> timedelta:
    """Offset that moves the latest timestamp to the same month/day in end_year."""
    values = list(moments)
    if not values:
        return timedelta(0)
    latest = max(values, key=_comparable)
    return _replace_year(latest, end_year) - latest


def shift_to_end_year(
    moments: Iterable[datetime], end_year: int = 2025
) -> list[datetime]:
    values = list(moments)
    offset = series_offset_to_end_year(values, end_year)
    return [moment + offset for moment in values]
