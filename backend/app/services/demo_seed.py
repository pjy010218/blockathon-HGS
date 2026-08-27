from __future__ import annotations

import os
from pathlib import Path

from app.adapters.community import CommunityDataAdapter
from app.adapters.enmods import EnmodsAdapter
from app.data.demo_sites import DEMO_SITES
from app.services.csv_import import DEFAULT_COMMUNITY_CSV, DEFAULT_EMS_CSV, DEFAULT_EMS_EVENTS, seed_from_files
from app.services.ingest import IngestService
from app.services.issuers import IssuerRegistry


def seed_synthetic(ingest: IngestService, issuers: IssuerRegistry | None = None) -> dict[str, int]:
    """Load curated Lower Mainland pairs into the in-memory ingest core.

    Government stations sit on the community coordinates so the 50 m matcher
    succeeds. Uses the same adapters as REST/CSV import.
    """

    from eth_account import Account

    government = Account.create()
    community = Account.create()
    if issuers is not None:
        issuers.allow(government.address, "government")
        issuers.allow(community.address, "community")

    enmods = EnmodsAdapter()
    community_adapter = CommunityDataAdapter()
    counts = {"government": 0, "community": 0}

    for site in DEMO_SITES:
        event = {
            "Location_ID": site["id"],
            "Location_Name": site["name"],
            "Location_Latitude": site["latitude"],
            "Location_Longitude": site["longitude"],
            "Observed_Date_Time": "2025-08-26T09:15:00-07:00",
            "Medium": site["area"],
            "observations": [
                {"Observed_Property_Name": code, "Result": value}
                for code, value in site["ems"].items()
            ],
        }
        ingest.upsert_government_station(
            location_id=site["id"],
            name=site["name"],
            latitude=site["latitude"],
            longitude=site["longitude"],
            medium=site["area"],
        )
        ingest.ingest(enmods.normalize(event), signer=government.address, anchor=True)
        counts["government"] += 1

        row = {
            "site": site["name"],
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "observed_at": "2025-06-05T17:00:00-07:00",
            "medium": "marine",
            **site["community"],
        }
        ingest.ingest(community_adapter.normalize(row), signer=community.address, anchor=True)
        counts["community"] += 1

    return counts


def seed_demo(ingest: IngestService, issuers: IssuerRegistry | None = None) -> dict[str, int]:
    """Prefer community CSV + this_yr.csv.gz; fall back to compact EMS JSON, then synthetic pairs."""

    community_csv = Path(os.getenv("COMMUNITY_CSV_PATH", DEFAULT_COMMUNITY_CSV))
    ems_csv = Path(os.getenv("EMS_CSV_PATH", DEFAULT_EMS_CSV))
    ems_events = Path(os.getenv("EMS_EVENTS_PATH", DEFAULT_EMS_EVENTS))
    if community_csv.is_file() and ems_csv.is_file():
        return seed_from_files(
            ingest,
            issuers,
            community_csv=community_csv,
            ems_csv=ems_csv,
            end_year=int(os.getenv("DEMO_END_YEAR", "2025")),
            shift_dates=True,
            anchor=True,
        )
    if community_csv.is_file() and ems_events.is_file():
        return seed_from_files(
            ingest,
            issuers,
            community_csv=community_csv,
            ems_events=ems_events,
            end_year=int(os.getenv("DEMO_END_YEAR", "2025")),
            shift_dates=True,
            anchor=True,
        )
    return seed_synthetic(ingest, issuers)
