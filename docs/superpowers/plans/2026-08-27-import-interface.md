# Import Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make community and government ingress match the approved spec: signed hashes, issuer roles, 50 m station matching, optional anchoring, EMS normalize-and-import.

**Architecture:** One ingest core. `POST /api/v1/records` is community-only (EIP-191 `personal_sign` over the canonical content hash, matching the existing frontend). `POST /api/v1/import/ems` accepts an EMS-shaped event, normalizes it, then uses the same ingest core with the `government` issuer role. Stations are in-memory, keyed by EMS `Location_ID`. Issuer checks use env allowlists so they work while `BLOCKCHAIN_MODE=simulated`.

**Tech Stack:** FastAPI, Pydantic v2, eth_account (via web3), existing `sha256_hex`.

## Global Constraints

- Signed bytes are the canonical content hash (hex SHA-256 of deterministic JSON), method `personal_sign`.
- Match metadata (`matched_station_*`, `displayable`, `match_status`) is outside the hash boundary.
- Missing / `NOT_DETECTED` is never converted to `0`.
- Simulated anchors stay labeled `simulated`. Mainnet anchoring remains refused.
- Do not commit credentials. Allowlists use checksummed addresses.
- No bulk CSV CLIs in this increment (community wide-row + 1.7 GB EMS stream remain follow-ups).

## File map

| File | Responsibility |
|---|---|
| `backend/app/models/parameters.py` | Canonical field ↔ EMS code map |
| `backend/app/models/schemas.py` | Record match fields, signed ingest, EMS import, Station |
| `backend/app/services/hashing.py` | Hash only canonical record fields |
| `backend/app/services/signatures.py` | Recover EIP-191 signer |
| `backend/app/services/issuers.py` | Env allowlist `community` / `government` |
| `backend/app/services/stations.py` | Station upsert + haversine matcher (50 m) |
| `backend/app/services/ingest.py` | Persist, hash, match, optional anchor, duplicate detect |
| `backend/app/adapters/enmods.py` | EMS event → `WaterQualityRecordCreate` |
| `backend/app/main.py` | Routes: records, stations, import/ems |
| `backend/tests/test_*.py` | Unit + API coverage from the spec |

---

### Task 1: Station matcher

**Files:**
- Create: `backend/app/services/stations.py`
- Test: `backend/tests/test_stations.py`

**Produces:** `Station`, `StationRegistry.upsert`, `StationRegistry.match(lat, lon) -> MatchResult | None` with threshold **50 m**.

- [ ] Tests: inside 50 m matches; 51 m unmatched; nearest of two stations
- [ ] Haversine in meters; key stations by `Location_ID`

---

### Task 2: Signatures + issuers

**Files:**
- Create: `backend/app/services/signatures.py`, `backend/app/services/issuers.py`
- Modify: `backend/app/services/hashing.py`
- Test: `backend/tests/test_signatures.py`

**Produces:**
- `canonical_record_payload(record) -> dict` (source, observed_at, location, measurements, metadata, raw_payload)
- `recover_signer(content_hash: str, signature: str) -> str`
- `IssuerRegistry.require(address, role) -> None` raising `PermissionError` if missing/wrong role

Frontend signs `personal_sign(["0x"+hash, address])` — recover with `encode_defunct(primitive=32-byte digest)`.

---

### Task 3: Enmods adapter

**Files:**
- Modify: `backend/app/adapters/enmods.py`
- Create: `backend/app/models/parameters.py`
- Test: `backend/tests/test_enmods.py`

**Produces:** `EnmodsAdapter.normalize(event) -> WaterQualityRecordCreate`

- Map `Observed_Property_Name` via EMS codes (`PH-F`/`0004` → `ph`, …)
- Skip unknown parameters
- `NOT_DETECTED` / empty → `value=None`, keep `raw_value`
- `raw_payload` = full event
- `source.kind=government`, `source_record_id` = `{Location_ID}-{Observed_Date_Time}`

---

### Task 4: Ingest API

**Files:**
- Modify: `backend/app/models/schemas.py`, `backend/app/main.py`, `backend/tests/test_api.py`
- Create: `backend/app/services/ingest.py`
- Modify: `.env.example`, `README.md`

**Produces:**
- `POST /api/v1/records` — community + signature required; 401/403/400/409 as spec; `displayable` from 50 m match; `anchor` optional
- `POST /api/v1/import/ems` — government issuer; upsert station; same ingest
- `GET /api/v1/stations`
- `GET /api/v1/records?include_unmatched=true` — default hides unmatched community
- Comparisons require shared station id when both have one

Issuer env: `COMMUNITY_ISSUERS`, `GOVERNMENT_ISSUERS` (comma-separated).
