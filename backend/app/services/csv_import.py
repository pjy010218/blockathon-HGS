from __future__ import annotations

import csv
import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.adapters.community import CommunityDataAdapter
from app.adapters.enmods import EnmodsAdapter
from app.services.ems_csv import grouped_ems_events
from app.services.dates import parse_observed_at, series_offset_to_end_year
from app.services.ingest import IngestService
from app.services.issuers import IssuerRegistry
from app.services.stations import Station, haversine_m

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_COMMUNITY_CSV = DATA_DIR / "dataset_download_5399.csv"
DEFAULT_EMS_EVENTS = DATA_DIR / "ems_lower_mainland.json"
DEFAULT_EMS_CSV = Path(__file__).resolve().parents[2] / "data" / "this_yr.csv.gz"


def _field(row: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for key in keys:
        if key in lowered and lowered[key] not in (None, ""):
            return lowered[key]
    return None


def _slug(name: str) -> str:
    return "-".join(name.strip().lower().split()) or "site"


def _read_community_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_ems_events(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("EMS events file must be a JSON list.")
    return payload


def _shift_ems_event(event: dict[str, Any], offset) -> dict[str, Any]:
    shifted = deepcopy(event)
    original = event.get("Observed_Date_Time")
    shifted["Observed_Date_Time"] = (parse_observed_at(event) + offset).isoformat()
    shifted["Original_Observed_Date_Time"] = original
    return shifted


def _nearest_event(events: list[dict[str, Any]], lat: float, lon: float) -> dict[str, Any]:
    return min(
        events,
        key=lambda event: haversine_m(
            lat,
            lon,
            float(event["Location_Latitude"]),
            float(event["Location_Longitude"]),
        ),
    )


def seed_from_files(
    ingest: IngestService,
    issuers: IssuerRegistry | None = None,
    *,
    community_csv: Path | str,
    ems_events: Path | str | None = None,
    ems_csv: Path | str | None = None,
    end_year: int = 2025,
    shift_dates: bool = True,
    anchor: bool = False,
) -> dict[str, int]:
    """Import community CSV + EMS JSON or gzip, shifting each series to end in end_year.

    False Creek community sites sit ~4 km from the nearest EMS station, so the
    50 m matcher would never pair them. For the demo map we copy nearest EMS
    chemistry onto the community coordinates. Original EMS coordinates stay in
    the government records at their true locations. Original source dates remain
    in ``raw_payload``.
    """

    from eth_account import Account

    government = Account.create()
    community = Account.create()
    if issuers is not None:
        issuers.allow(government.address, "government")
        issuers.allow(community.address, "community")

    community_adapter = CommunityDataAdapter()
    enmods = EnmodsAdapter()
    rows = _read_community_rows(Path(community_csv))
    if ems_csv is not None:
        events = grouped_ems_events(Path(ems_csv))
    elif ems_events is not None:
        events = _read_ems_events(Path(ems_events))
    else:
        raise ValueError("Provide ems_csv or ems_events.")
    if not rows:
        raise ValueError("Community CSV has no rows.")
    if not events:
        raise ValueError("EMS events file is empty.")

    community_offset = (
        series_offset_to_end_year([parse_observed_at(row) for row in rows], end_year)
        if shift_dates
        else timedelta(0)
    )
    ems_offset = (
        series_offset_to_end_year([parse_observed_at(event) for event in events], end_year)
        if shift_dates
        else timedelta(0)
    )

    counts = {"government": 0, "community": 0}
    sites: dict[tuple[str, float, float], dict[str, Any]] = {}
    for row in rows:
        name = str(
            _field(row, "location name", "location_name", "site", "name") or "community site"
        ).strip()
        lat = float(_field(row, "latitude", "lat"))
        lon = float(_field(row, "longitude", "lon"))
        sites.setdefault((name, round(lat, 5), round(lon, 5)), {
            "name": name,
            "latitude": lat,
            "longitude": lon,
        })

    aligned_payloads: list = []
    aligned_stations: list[Station] = []
    for site in sites.values():
        aligned = _shift_ems_event(
            _nearest_event(events, site["latitude"], site["longitude"]), ems_offset
        )
        aligned["Location_ID"] = f"DEMO-{_slug(site['name'])}"
        aligned["Location_Name"] = site["name"]
        aligned["Location_Latitude"] = site["latitude"]
        aligned["Location_Longitude"] = site["longitude"]
        aligned_stations.append(
            Station(
                id=str(aligned["Location_ID"]),
                name=site["name"],
                latitude=site["latitude"],
                longitude=site["longitude"],
                medium=aligned.get("Medium"),
            )
        )
        aligned_payloads.append(enmods.normalize(aligned))

    station_by_id: dict[str, Station] = {}
    gov_payloads = []
    for event in events:
        shifted = _shift_ems_event(event, ems_offset)
        location_id = str(shifted["Location_ID"])
        station_by_id[location_id] = Station(
            id=location_id,
            name=shifted.get("Location_Name") or location_id,
            latitude=float(shifted["Location_Latitude"]),
            longitude=float(shifted["Location_Longitude"]),
            medium=shifted.get("Medium"),
        )
        gov_payloads.append(enmods.normalize(shifted))

    ingest.store.save_stations(aligned_stations + list(station_by_id.values()))

    counts["government"] += ingest.ingest_many(
        aligned_payloads, signer=government.address, anchor=anchor
    )
    counts["government"] += ingest.ingest_many(
        gov_payloads, signer=government.address, anchor=anchor
    )

    for row in rows:
        shifted_row = dict(row)
        shifted_row["observed_at"] = (parse_observed_at(row) + community_offset).isoformat()
        ingest.ingest(community_adapter.normalize(shifted_row), signer=community.address, anchor=anchor)
        counts["community"] += 1

    return counts
