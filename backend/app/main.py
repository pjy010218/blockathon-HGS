from __future__ import annotations

import os
import sys
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.enmods import EnmodsAdapter
from app.models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    EmsImportRequest,
    MapSite,
    SignedRecordRequest,
    SourceKind,
    StationResponse,
    WaterQualityRecord,
    WaterQualityRecordCreate,
)
from app.services.blockchain import BlockchainService
from app.services.comparison import compare_records
from app.services.database import MemoryRecordStore, open_store
from app.services.hashing import content_hash_for_record
from app.services.ingest import DuplicateRecord, IngestService
from app.services.issuers import IssuerRegistry
from app.services.map_sites import build_map_sites
from app.services.signatures import SignatureError, recover_signer

app = FastAPI(
    title="Community Water Audit Trail API",
    version="0.1.0",
    description=(
        "A provenance and verification API. It displays source records and their "
        "differences without assigning trust scores or declaring a preferred source."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = MemoryRecordStore() if "pytest" in sys.modules else open_store(os.getenv("DATABASE_URL"))
if store is None:
    raise RuntimeError("DATABASE_URL is required. Records are stored in Postgres, not in process memory.")
issuers = IssuerRegistry()
blockchain = BlockchainService(
    mode=os.getenv("BLOCKCHAIN_MODE", "simulated"),
    network=os.getenv("BLOCKCHAIN_NETWORK", "local"),
)
ingest = IngestService(store, blockchain)
enmods = EnmodsAdapter()

if (
    "pytest" not in sys.modules
    and os.getenv("DEMO_SEED", "").strip().lower() in {"1", "true", "yes"}
    and store.count() == 0
):
    from app.services.demo_seed import seed_demo

    seed_demo(ingest, issuers)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "water-audit-api"}


@app.get("/api/v1/stations", response_model=list[StationResponse])
def list_stations() -> list[StationResponse]:
    return [
        StationResponse(
            id=station.id,
            name=station.name,
            latitude=station.latitude,
            longitude=station.longitude,
            medium=station.medium,
        )
        for station in store.list_stations()
    ]


@app.get("/api/v1/map", response_model=list[MapSite])
def list_map_sites() -> list[MapSite]:
    return build_map_sites(store.records_for_map())


@app.get("/api/v1/records", response_model=list[WaterQualityRecord])
def list_records(include_unmatched: bool = Query(default=False)) -> list[WaterQualityRecord]:
    return store.all_records(include_unmatched=include_unmatched)


@app.post(
    "/api/v1/records",
    response_model=WaterQualityRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_record(payload: SignedRecordRequest) -> WaterQualityRecord:
    _require_supported_signature_method(payload.signature_method)
    if payload.source.kind != SourceKind.community:
        raise HTTPException(
            status_code=400,
            detail="Government records use POST /api/v1/import/ems.",
        )
    canonical = _canonical_record(payload)
    return _authenticated_ingest(
        canonical,
        signature=payload.signature,
        claimed_address=payload.signer_address,
        signed_hash=payload.signed_content_hash,
        role="community",
        anchor=payload.anchor,
    )


@app.post(
    "/api/v1/import/ems",
    response_model=WaterQualityRecord,
    status_code=status.HTTP_201_CREATED,
)
def import_ems(payload: EmsImportRequest) -> WaterQualityRecord:
    _require_supported_signature_method(payload.signature_method)
    event = payload.event.model_dump(mode="python")
    try:
        canonical = enmods.normalize(event)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    record = _authenticated_ingest(
        canonical,
        signature=payload.signature,
        claimed_address=payload.signer_address,
        signed_hash=payload.signed_content_hash,
        role="government",
        anchor=payload.anchor,
    )
    ingest.upsert_government_station(
        location_id=payload.event.Location_ID,
        name=payload.event.Location_Name,
        latitude=payload.event.Location_Latitude,
        longitude=payload.event.Location_Longitude,
        medium=payload.event.Medium,
    )
    return record


@app.get("/api/v1/records/{record_id}", response_model=WaterQualityRecord)
def get_record(record_id: UUID) -> WaterQualityRecord:
    record = store.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.post("/api/v1/records/{record_id}/anchor", response_model=WaterQualityRecord)
def anchor_record(record_id: UUID) -> WaterQualityRecord:
    record = store.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.blockchain.status.value in {"anchored", "simulated"}:
        return record

    try:
        record.blockchain = blockchain.anchor(
            record.content_hash,
            source=record.source.kind.value,
            source_record_id=record.source.source_record_id or str(record.id),
            attributed_to=record.signer_address,
        )
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    store.save_record(record)
    return record


@app.get("/api/v1/records/{record_id}/verify")
def verify_record(record_id: UUID) -> dict[str, object]:
    record = store.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")

    recalculated_hash = content_hash_for_record(record)
    return {
        "record_id": record.id,
        "stored_hash": record.content_hash,
        "recalculated_hash": recalculated_hash,
        "matches": recalculated_hash == record.content_hash,
        "anchor": record.blockchain,
    }


@app.post("/api/v1/comparisons", response_model=ComparisonResponse)
def compare(request: ComparisonRequest) -> ComparisonResponse:
    government = store.get_record(request.government_record_id)
    community = store.get_record(request.community_record_id)
    if government is None or community is None:
        raise HTTPException(status_code=404, detail="One or both records not found")
    if (
        community.matched_station_id
        and government.matched_station_id
        and community.matched_station_id != government.matched_station_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Comparisons require community and government records from the same station.",
        )

    return ComparisonResponse(
        government_record_id=government.id,
        community_record_id=community.id,
        fields=compare_records(government, community),
        notes=[
            "Comparison is descriptive only; no source is ranked or marked as more trustworthy.",
            "Missing fields remain visible rather than being treated as zero or equal.",
        ],
    )


def _canonical_record(payload: SignedRecordRequest) -> WaterQualityRecordCreate:
    return WaterQualityRecordCreate.model_validate(
        payload.model_dump(
            exclude={
                "signature",
                "signer_address",
                "signed_content_hash",
                "signature_method",
                "anchor",
            }
        )
    )


def _require_supported_signature_method(signature_method: str) -> None:
    if signature_method != "personal_sign":
        raise HTTPException(status_code=400, detail="Unsupported signature method.")


def _authenticated_ingest(
    canonical: WaterQualityRecordCreate,
    *,
    signature: str | None,
    claimed_address: str | None,
    signed_hash: str | None,
    role: str,
    anchor: bool,
) -> WaterQualityRecord:
    if not signature or not signed_hash:
        raise HTTPException(status_code=401, detail="A wallet signature over the content hash is required.")
    digest = content_hash_for_record(canonical)
    if signed_hash.removeprefix("0x").lower() != digest.lower():
        raise HTTPException(
            status_code=400,
            detail="The signed record did not match the submitted record.",
        )

    try:
        recovered = recover_signer(digest, signature)
    except SignatureError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    if claimed_address and recovered.lower() != claimed_address.lower():
        raise HTTPException(status_code=401, detail="The signature does not match the claimed signer.")

    try:
        issuers.require(recovered, role)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    try:
        return ingest.ingest(canonical, signer=recovered, anchor=anchor)
    except DuplicateRecord as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
