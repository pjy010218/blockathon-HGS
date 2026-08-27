from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Any, Iterable

from app.models.parameters import canonical_field_for_ems_code

EMS_CODES = frozenset(
    {
        "0004",
        "PH-F",
        "DO-F",
        "0011",
        "EC-F",
        "SC-F",
        "TEMF",
        "1110",
        "1111",
        "1107",
        "0147",
    }
)


def _open_text(path: Path):
    if path.suffix == ".gz" or path.name.endswith(".csv.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open(newline="", encoding="utf-8", errors="replace")


def grouped_ems_events(path: Path | str) -> list[dict[str, Any]]:
    """Stream an EMS observation CSV/gzip into grouped events.

    Rows are filtered to the shared Community↔EMS parameter codes, then merged
    by Location_ID + Observed_Date_Time + Medium. Unmapped-only groups are dropped.
    """

    source = Path(path)
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    with _open_text(source) as handle:
        for row in csv.DictReader(handle):
            code = str(row.get("Observed_Property_Name") or "").strip()
            if canonical_field_for_ems_code(code) is None and code.upper() not in EMS_CODES:
                continue
            try:
                latitude = float(row.get("Location_Latitude"))
                longitude = float(row.get("Location_Longitude"))
            except (TypeError, ValueError):
                continue
            location_id = str(row.get("Location_ID") or "").strip()
            observed_at = str(row.get("Observed_Date_Time") or "").strip()
            medium = str(row.get("Medium") or "").strip()
            if not location_id or not observed_at:
                continue
            key = (location_id, observed_at, medium)
            event = groups.get(key)
            if event is None:
                event = {
                    "Location_ID": location_id,
                    "Location_Name": row.get("Location_Name"),
                    "Location_Latitude": latitude,
                    "Location_Longitude": longitude,
                    "Observed_Date_Time": observed_at,
                    "Medium": medium,
                    "observations": [],
                }
                groups[key] = event
            event["observations"].append(
                {
                    "Observed_Property_Name": code,
                    "Result": row.get("Result_Value") if row.get("Result_Value") not in (None, "") else row.get("Result"),
                    "Unit": row.get("Result_Unit") if row.get("Result_Unit") not in (None, "") else row.get("Unit"),
                    "Detection_Condition": row.get("Detection_Condition"),
                }
            )
    return [event for event in groups.values() if event["observations"]]
