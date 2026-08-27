# Import Interface Design

**Date:** 2026-08-27  
**Status:** Draft for implementation planning  
**Project:** Water Audit Trail (SDG 14 / Blockathon)

## Goal

Define how water-quality data enters the system from two actor groups—**community** and **government/authority**—while preserving provenance, computing a content hash, optionally anchoring on-chain, and binding each push to a **registered Ethereum issuer identity**.

This design covers ingress only (submit, bulk import, daily push, station matching). Comparison and viewer UX stay as they are unless noted.

## Decisions (summary)

| Topic | Decision |
|---|---|
| Architecture | Dual ingress, one canonical ingest core |
| Community ongoing | Frontend form → `POST /api/v1/records` (canonical JSON) + MetaMask signature |
| Community first load | CLI bulk of `dataset_download_5399.csv` via `CommunityDataAdapter` |
| Gov first load | Streaming CLI of large EMS CSV (~1.7 GB) |
| Gov ongoing | REST `POST /api/v1/import/ems` with EMS-shaped JSON + service-wallet signature |
| EMS record shape | Filter shared parameters, then group by `Location_ID` + `Observed_Date_Time` + `Medium` |
| Anchor after import | Optional flag `anchor=true\|false`, default `false` |
| Identity | Ethereum wallet signature over content hash; on-chain `registerIssuer(address, role)` |
| Gov automation | Unattended service wallet (hot key); same signature rules as interactive wallets |
| Station linking | Community snaps to nearest Gov station within **50 m**; unmatched records are stored but **not shown** in the default viewer |
| Trust posture | No trust scores; issuer proves who submitted, not that the reading is “true” |

## Architecture

```text
Community Form (Next.js + MetaMask)
        │ canonical JSON + signature
        ▼
Community CSV CLI ──► CommunityDataAdapter ──┐
                                              │
Gov EMS REST ──► EnmodsAdapter ───────────────┼──► Signature + Issuer check
Gov EMS CSV CLI (stream) ──► EnmodsAdapter ───┘              │
                                                            ▼
                                                    IngestService
                                                    (store + content_hash)
                                                            │
                                              optional anchor ──► WaterAuditRegistry
                                                            │
                                                    StationMatcher (community)
```

**Principles (aligned with `DEV_GUIDE.md` / `README.md`):**

- Raw payloads stay off-chain; on-chain stores hash + minimal metadata + submitter.
- Never invent missing values (`NOT_DETECTED` ≠ `0`).
- Keep `raw_payload`; do not drop unmapped upstream fields.
- Clearly label `simulated` vs real blockchain anchors.

## Components

| Component | Responsibility |
|---|---|
| Community Form | Collect canonical readings; compute hash client-side; request MetaMask signature; `POST /api/v1/records` |
| Community CSV CLI | Stream/read `dataset_download_5399.csv`; normalize; sign with community issuer wallet; ingest |
| Gov EMS REST | Accept EMS JSON (+ signature); normalize via `EnmodsAdapter`; ingest |
| Gov EMS CSV CLI | Stream large CSV; shared-param filter; event grouping; normalize; sign; ingest |
| `CommunityDataAdapter` | Wide community row → `WaterQualityRecordCreate` (`source.kind=community`) |
| `EnmodsAdapter` | EMS observation/event → canonical record (`source.kind=government`) |
| `StationRegistry` | Upsert stations from Gov imports (`Location_ID`, name, lat, lon, medium/type metadata) |
| `StationMatcher` | Haversine (or equivalent) nearest-station search; threshold **50 m** |
| `SignatureService` | Verify EIP-191 or EIP-712 signature over the **canonical content hash**; recover address |
| `IssuerRegistry` (contract + API check) | `registerIssuer(address, role)`; reject push if signer missing or wrong role |
| `IngestService` | Validate → persist → hash; optional anchor; apply station match for community |
| `WaterAuditRegistry.sol` | Extend current anchor contract with issuer roles (see Contract changes) |
| Viewer | Default lists only community records with a successful station match |

## Data flows

### A — Community form (ongoing)

1. User submits station context, `observed_at`, medium, and readings.
2. Frontend builds canonical JSON and the same deterministic content hash the backend uses.
3. MetaMask signs that hash.
4. `POST /api/v1/records` with body + `signature` (+ recovered/claimed `signerAddress` for UX).
5. Backend recovers signer → requires issuer role `community` → verifies hash → `StationMatcher` → persist (`displayable` from match) → optional anchor.

### B — Community bulk (first load)

1. CLI reads `dataset_download_5399.csv` (wide format: one row ≈ one multi-parameter sample; ~74 rows in the reference file).
2. `CommunityDataAdapter.normalize(row)` → record; `raw_payload` = original row.
3. Sign each canonical hash with the community issuer wallet.
4. Same ingest path as A, including station matching.

### C — Gov daily REST

1. Gov job maps EMS payload with the same rules as `EnmodsAdapter`, computes the canonical content hash, and signs that hash with the service wallet.
2. Job `POST`s EMS-shaped JSON + `signature` (+ claimed address) to `/api/v1/import/ems`.
3. Backend runs `EnmodsAdapter`, recomputes the hash, verifies the signature covers that hash, recovers the signer, requires issuer role `government`, ingests, upserts `StationRegistry`, optionally anchors.

The HTTP body may remain EMS-shaped for operator convenience; the signature **always** covers the canonical content hash, never the raw EMS string alone.

### D — Gov bulk CSV (~1.7 GB)

1. CLI streams the file (no full in-memory load).
2. Keep rows whose `Observed_Property_Name` (EMS code) is in the shared-parameter set (see Parameters).
3. Group by `Location_ID` + `Observed_Date_Time` + `Medium`.
4. Adapter → sign with gov issuer wallet → ingest → station upsert.
5. Print summary: `created`, `skipped_unmatched_params`, `duplicates`, `errors[]`.

## Station matching (community → gov)

**Rule:** Community records must be linkable to a government station to appear in the default UI.

1. Gov ingest upserts stations into `StationRegistry` keyed by `Location_ID` with coordinates from EMS (`Location_Latitude` / `Location_Longitude`) and display name (`Location_Name`).
2. On community ingest, find nearest station by coordinates.
3. If distance ≤ **50 m**:
   - set `matched_station_id`, `matched_station_name`, `match_distance_m`
   - set `displayable = true`
4. If no station within 50 m:
   - still persist and hash the record
   - `matched_station_id = null`, `displayable = false`, `match_status = unmatched`
   - API response informs the client that the record will not appear in the default viewer
5. `GET /api/v1/records` defaults to `displayable=true` (or equivalent filter). Support `include_unmatched=true` for debug/demo.
6. Comparisons only pair community and government records that share the same `matched_station_id` / gov `Location_ID`.

**Hash boundary:** Match metadata (`matched_station_*`, `displayable`, `match_distance_m`) is **not** part of the content hash input. Re-matching after new gov stations are imported must not invalidate historical hashes. Optional later: a re-match job updates only match fields.

**Demo caveat:** Reference community sites (e.g. False Creek 2019) may not fall within 50 m of real EMS rows. For demos, seed gov stations near community coordinates or use a curated EMS subset so matching succeeds.

## Shared parameters (EMS ↔ community)

Canonical intersection used for EMS filtering and community mapping:

| Canonical | Community CSV columns (examples) | EMS codes (examples) |
|---|---|---|
| pH | `ph (std_units, …)` | `0004`, `PH-F` |
| dissolved_oxygen | `oxygen (mg_l, …)` | `DO-F` |
| conductivity | `conductivity (us_cm, …)` | `0011`, `EC-F`, `SC-F` |
| temperature | `water_temperature (deg_c, …)` | `TEMF` |
| nitrate | `nitrates (mg_l, …)` | `1110` |
| nitrite | `nitrites (mg_l, …)` | `1111` |
| hardness | `hardness (mg_l, …)` | `1107` |
| e_coli | `e_coli (cfu_per_100ml, …)` | `0147` |

Unmapped EMS parameters are skipped in bulk import counts (`skipped_unmatched_params`), not forced into canonical measurements. Full row data for ingested events remains in `raw_payload` as applicable.

## Identity & contract changes

### Signing

- Algorithm: EIP-191 personal sign or EIP-712 typed data (pick one in implementation plan; prefer **EIP-712** if time allows for clearer domain separation).
- Signed bytes: canonical **content hash** (hex digest of deterministic JSON used by `sha256_hex` today).
- Community: interactive MetaMask.
- Government: automated service wallet; private key in env/vault for hackathon; production would use HSM/KMS.

### Issuer registry

Extend `WaterAuditRegistry` (or companion contract) with:

- `registerIssuer(address account, bytes32 role)` — admin/owner only in MVP (`community` | `government`)
- `revokeIssuer(address account)`
- `isIssuer(address account, bytes32 role) view`
- `anchorRecord` — require `msg.sender` is a registered issuer (or backend relays and passes recovered signer—see below)

**Backend gate (MVP):** Even when anchoring is simulated, the API **must** verify the signature and check the issuer registry (on-chain when available, or a mirrored allowlist synced from the contract). Reject with `403` if not allowed.

**Relayer note:** If the backend submits the chain tx, `msg.sender` is the relayer. In that mode, store `recoveredSigner` in the anchor event/metadata and still enforce issuer checks off-chain before relay. Document which mode is active (`BLOCKCHAIN_MODE`).

### Existing contract

Current `anchorRecord(bytes32,string,string)` already stores `submitter = msg.sender`. Design adds explicit roles so gov and community keys cannot impersonate each other at the API boundary.

## API surface (additions)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/records` | Existing; require signature + community issuer; run station match |
| `POST` | `/api/v1/import/ems` | Gov EMS JSON push; government issuer; normalize + ingest; query/body flag `anchor` |
| `GET` | `/api/v1/stations` | List gov stations (for form hints / debug) |
| `GET` | `/api/v1/records` | Default exclude unmatched community (`include_unmatched`) |

CLIs are first-class for bulk; they may call ingest services in-process rather than HTTP when handling multi-GB files.

## Error handling

| Case | Response / behavior |
|---|---|
| Missing/invalid signature | `401` / `400` |
| Signer not registered or wrong role | `403` |
| Payload hash ≠ signed hash | `400` |
| EMS row outside shared params (bulk) | skip + count |
| `NOT_DETECTED` / empty result | no fabricated zero; keep raw + detection metadata |
| Invalid coordinates/time | reject record; bulk continues with `errors[]` |
| Duplicate content hash | idempotent return of existing record or `409` with id; do not double-anchor |
| Unmatched community station | `201` with `displayable=false` |
| Simulated chain | status `simulated`, never labeled as confirmed mainnet |

PII such as `Field_Visit_Participants` stays in `raw_payload` only and is not placed in on-chain metadata.

## Testing scope

- Adapter unit tests for community wide-row and EMS group/filter edge cases.
- StationMatcher: inside 50 m / outside 50 m.
- Signature + wrong role + hash mismatch API tests.
- Default list hides unmatched; `include_unmatched=true` shows them.
- CLI smoke on community CSV and EMS 10k sample (not full 1.7 GB in CI).
- Contract tests for issuer registration and restricted anchoring (local/simulated).

Out of scope for MVP tests: mainnet deployment, mTLS/X.509, production KMS.

## Non-goals (MVP)

- Reviewer/attestation role separate from submitter.
- Trust scores or “preferred source” ranking.
- HTTP upload of the 1.7 GB file.
- Automatic re-match job (document as follow-up).
- Perfect geo alignment of historical False Creek vs province-wide EMS without demo seeding.

## Follow-ups

1. Re-match job when new gov stations arrive.
2. On-chain issuer registry fully authoritative (no env allowlist mirror).
3. Durable DB instead of in-memory store before any shared deployment.
4. EIP-712 domain versioning for hash/signature stability across releases.

## Approval

Design reviewed in brainstorming session (approach 1 + station matching B @ 50 m). Ready for implementation plan via `writing-plans` after stakeholder sign-off on this file.
