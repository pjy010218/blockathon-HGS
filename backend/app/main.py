from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    WaterQualityRecord,
    WaterQualityRecordCreate,
)
from app.services.blockchain import BlockchainService
from app.services.comparison import compare_records
from app.services.hashing import sha256_hex

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
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

records: dict[UUID, WaterQualityRecord] = {}
blockchain = BlockchainService(
    mode=os.getenv("BLOCKCHAIN_MODE", "simulated"),
    network=os.getenv("BLOCKCHAIN_NETWORK", "local"),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "water-audit-api"}


@app.get("/api/v1/records", response_model=list[WaterQualityRecord])
def list_records() -> list[WaterQualityRecord]:
    return list(records.values())


@app.post(
    "/api/v1/records",
    response_model=WaterQualityRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_record(payload: WaterQualityRecordCreate) -> WaterQualityRecord:
    ingested_at = datetime.now(timezone.utc)
    content = payload.model_dump(mode="json")
    record = WaterQualityRecord(
        **content,
        ingested_at=ingested_at,
        content_hash=sha256_hex(content),
    )
    records[record.id] = record
    return record


@app.get("/api/v1/records/{record_id}", response_model=WaterQualityRecord)
def get_record(record_id: UUID) -> WaterQualityRecord:
    record = records.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.post("/api/v1/records/{record_id}/anchor", response_model=WaterQualityRecord)
def anchor_record(record_id: UUID) -> WaterQualityRecord:
    record = records.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.blockchain.status.value in {"anchored", "simulated"}:
        return record

    try:
        record.blockchain = blockchain.anchor(record.content_hash)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return record


@app.get("/api/v1/records/{record_id}/verify")
def verify_record(record_id: UUID) -> dict[str, object]:
    record = records.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")

    payload = record.model_dump(
        mode="json", exclude={"id", "ingested_at", "content_hash", "blockchain"}
    )
    recalculated_hash = sha256_hex(payload)
    return {
        "record_id": record.id,
        "stored_hash": record.content_hash,
        "recalculated_hash": recalculated_hash,
        "matches": recalculated_hash == record.content_hash,
        "anchor": record.blockchain,
    }


@app.post("/api/v1/comparisons", response_model=ComparisonResponse)
def compare(request: ComparisonRequest) -> ComparisonResponse:
    government = records.get(request.government_record_id)
    community = records.get(request.community_record_id)
    if government is None or community is None:
        raise HTTPException(status_code=404, detail="One or both records not found")

    return ComparisonResponse(
        government_record_id=government.id,
        community_record_id=community.id,
        fields=compare_records(government, community),
        notes=[
            "Comparison is descriptive only; no source is ranked or marked as more trustworthy.",
            "Missing fields remain visible rather than being treated as zero or equal.",
        ],
    )
