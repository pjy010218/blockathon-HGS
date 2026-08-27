from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceKind(str, Enum):
    government = "government"
    community = "community"
    other = "other"


class SourceProvenance(BaseModel):
    """Where a record came from; this is descriptive, not a trust rating."""

    model_config = ConfigDict(extra="allow")

    kind: SourceKind
    provider: str = Field(min_length=1)
    dataset_id: str | None = None
    source_record_id: str | None = None
    source_url: HttpUrl | None = None
    retrieved_at: datetime | None = None


class Location(BaseModel):
    name: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Measurement(BaseModel):
    field: str = Field(min_length=1, description="Canonical or source field name")
    value: float | int | str | bool | None = None
    unit: str | None = None
    raw_value: Any | None = None
    method: str | None = None


class WaterQualityRecordCreate(BaseModel):
    source: SourceProvenance
    observed_at: datetime
    location: Location
    measurements: list[Measurement] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Original source-shaped payload, retained for auditability.",
    )


class SignedRecordRequest(WaterQualityRecordCreate):
    """Community ingest envelope. Signature fields are not part of the hash."""

    model_config = ConfigDict(populate_by_name=True)

    signature: str | None = None
    signer_address: str | None = Field(default=None, alias="signerAddress")
    signed_content_hash: str | None = Field(default=None, alias="signedContentHash")
    signature_method: str = Field(default="personal_sign", alias="signatureMethod")
    anchor: bool = False


class EmsObservation(BaseModel):
    model_config = ConfigDict(extra="allow")

    Observed_Property_Name: str
    Result: Any = None
    Unit: str | None = None


class EmsEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    Location_ID: str
    Location_Name: str | None = None
    Location_Latitude: float
    Location_Longitude: float
    Observed_Date_Time: str
    Medium: str | None = None
    observations: list[EmsObservation] = Field(default_factory=list)


class EmsImportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: EmsEvent
    signature: str | None = None
    signer_address: str | None = Field(default=None, alias="signerAddress")
    signed_content_hash: str | None = Field(default=None, alias="signedContentHash")
    signature_method: str = Field(default="personal_sign", alias="signatureMethod")
    anchor: bool = False


class StationResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    medium: str | None = None


class AnchorStatus(str, Enum):
    not_anchored = "not_anchored"
    simulated = "simulated"
    anchored = "anchored"


class BlockchainAnchor(BaseModel):
    status: AnchorStatus = AnchorStatus.not_anchored
    network: str | None = None
    contract_address: str | None = None
    transaction_hash: str | None = None
    block_number: int | None = None
    anchored_at: datetime | None = None


class WaterQualityRecord(WaterQualityRecordCreate):
    id: UUID = Field(default_factory=uuid4)
    ingested_at: datetime
    content_hash: str
    blockchain: BlockchainAnchor = Field(default_factory=BlockchainAnchor)
    signer_address: str | None = None
    displayable: bool = True
    matched_station_id: str | None = None
    matched_station_name: str | None = None
    match_distance_m: float | None = None
    match_status: str | None = None


class ComparisonRequest(BaseModel):
    government_record_id: UUID
    community_record_id: UUID


class ComparisonField(BaseModel):
    field: str
    government: Measurement | None = None
    community: Measurement | None = None
    status: str = Field(
        description="Neutral relationship label; it is not a trust or quality judgment."
    )


class ComparisonResponse(BaseModel):
    government_record_id: UUID
    community_record_id: UUID
    fields: list[ComparisonField]
    notes: list[str] = Field(default_factory=list)
