"""Streaming grouping helpers for community and EMS rows."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any


def ems_group_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("Location_ID", row.get("location_id", ""))).strip(),
        str(row.get("Observed_Date_Time", row.get("observed_at", ""))).strip(),
        str(row.get("Medium", row.get("medium", ""))).strip(),
    )


def community_group_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return the sampling-event key used by the real community CSV."""

    return (
        str(row.get("MonitoringLocationID", "")).strip(),
        str(row.get("ActivityStartDate", "")).strip(),
        str(row.get("ActivityStartTime", "")).strip(),
        str(row.get("ActivityMediaName", "")).strip(),
    )


def group_ems_rows(rows: Iterable[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    """Yield contiguous EMS groups without loading the input into memory.

    The source must be ordered by ``Location_ID``, ``Observed_Date_Time`` and
    ``Medium``. This is necessary for bounded-memory grouping of a multi-GB file.
    """

    current_key: tuple[str, str, str] | None = None
    current: list[dict[str, Any]] = []
    for row in rows:
        key = ems_group_key(row)
        if current and key != current_key:
            yield current
            current = []
        current_key = key
        current.append(row)
    if current:
        yield current


def group_community_rows(rows: Iterable[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    """Yield contiguous community sampling events without loading all rows."""

    current_key: tuple[str, str, str, str] | None = None
    current: list[dict[str, Any]] = []
    for row in rows:
        key = community_group_key(row)
        if current and key != current_key:
            yield current
            current = []
        current_key = key
        current.append(row)
    if current:
        yield current
