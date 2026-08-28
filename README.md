# Tideproof — Water Audit Trail

Tideproof is an SDG 14 project for preserving and comparing community and government water-quality records in British Columbia. It makes changes detectable, keeps provenance visible, and lets readers inspect differences without declaring which source is correct.

The project combines a public-facing Next.js application, a FastAPI ingestion and comparison service, and an Ethereum record-hash registry.

## Project status

Tideproof is currently a hackathon prototype with a production-oriented integration design.

| Area | Available now | Planned next |
|---|---|---|
| Map | Interactive Vancouver-area map with clearly labeled prototype comparisons | Load only station-matched records and comparisons from the API |
| Community data | Canonical form, MetaMask signature, backend recovery, issuer allowlist, 50 m station matching | Durable storage and CSV bulk import |
| Stations | In-memory registry from EMS import; `GET /api/v1/stations` | PostgreSQL-backed station directory |
| Leaderboard | Responsive placeholder contribution history | Rankings calculated from accepted, issuer-signed records |
| API | Signed community ingest, signed EMS import, unmatched filtering, verification, comparison, optional anchoring | Streaming EMS CSV CLI and community CSV CLI |
| Blockchain | WaterAuditRegistry with issuer roles on Sepolia; backend simulated by default, `BLOCKCHAIN_MODE=ethereum` on testnet | Query on-chain `isIssuer` instead of the env allowlist |

The API verifies community and government signatures, checks issuer allowlists, matches community records to government stations within 50 metres, and hides unmatched community records from the default list. Bulk CSV CLIs and a durable database are still pending.

Put the community MetaMask address in `COMMUNITY_ISSUERS` and the government service wallet in `GOVERNMENT_ISSUERS` (comma-separated). Unsigned pushes are rejected.

## User experience

### Map

The default view centers on Vancouver and the Lower Mainland. Smiley markers indicate that the displayed community and EMS readings meet a comparison rule; frowny markers indicate that a difference needs review.

The current markers are prototype data. The completed viewer will show only community records matched to a government station within 50 metres and will compare records that share that station identity.

### Data

Community contributors can:

1. Connect a MetaMask wallet.
2. Enter station context, observation time, medium, coordinates, and measurements.
3. Build and hash a canonical record in the browser.
4. Sign the content hash with MetaMask.
5. Send the signed record to the community ingestion endpoint.
6. Request blockchain anchoring when desired; the default is off.

The backend remains authoritative for signature recovery, registered issuer status, duplicate detection, station matching, persistence, and anchoring.

### Leaderboard

The leaderboard is designed to recognize sustained participation and make contribution history easy to inspect. It is not a trust score: a registered issuer proves who submitted a record, not whether the reading is true.

## Shared water-quality parameters

Community submissions and EMS comparisons use this canonical intersection:

| Canonical parameter | Community source | EMS codes | Display unit |
|---|---|---|---|
| pH | `ph` | `0004`, `PH-F` | pH |
| Dissolved oxygen | `oxygen` | `DO-F` | mg/L |
| Conductivity | `conductivity` | `0011`, `EC-F`, `SC-F` | µS/cm |
| Water temperature | `water_temperature` | `TEMF` | °C |
| Nitrate | `nitrates` | `1110` | mg/L |
| Nitrite | `nitrites` | `1111` | mg/L |
| Hardness | `hardness` | `1107` | mg/L as CaCO₃ |
| E. coli | `e_coli` | `0147` | CFU/100mL; EMS may report MPN/100mL |

Missing and not-detected values are never converted to zero. Unmapped upstream fields remain part of the retained raw payload where applicable.

## Intended architecture

```text
Community form ── canonical record + wallet signature ──┐
Community CSV import ────────────────────────────────────┤
                                                        ├─► validation and issuer check
Government EMS REST push ────────────────────────────────┤          │
Government EMS CSV import ───────────────────────────────┘          ▼
                                                             ingest and hash
                                                                  │
                                            station match ◄────────┤
                                            optional anchor ◄──────┘
```

- Community contributors use an interactive MetaMask wallet.
- Government automation uses a service wallet under the same signature and role rules.
- Raw measurements remain off-chain.
- Ethereum stores the content hash and minimal provenance metadata.
- Community records remain stored when unmatched, but the default viewer hides them.
- Station-match metadata sits outside the content-hash boundary so records can be rematched later.

The approved ingress design is documented in [Import Interface Design](docs/superpowers/specs/2026-08-27-import-interface-design.md).

## Repository structure

```text
backend/
  app/main.py                  Current FastAPI routes and in-memory store
  app/adapters/                Community and government adapter boundaries
  app/models/                  Provenance, measurement, and comparison models
  app/services/                Hashing, comparison, and blockchain services
  tests/                       Backend API tests
frontend/
  app/                         Next.js application and visual system
  components/                  Map and record interfaces
  lib/                         API, signing, schema, and shared frontend types
contracts/
  WaterAuditRegistry.sol       Initial Ethereum content-hash registry
docs/superpowers/specs/        Approved and draft technical designs
governance_and_regulatory/     Governance guidelines and readiness checklist
```

See [CHANGELOG.md](CHANGELOG.md) for a quick history of project progress and [DEV_GUIDE.md](DEV_GUIDE.md) for development controls and conventions.

## Local development

Frontend (port 3000) and API (port 8000) run as separate processes. CORS already allows `http://localhost:3000`.

### Requirements

- Node.js 20 or newer
- Python 3.11 or newer
- Docker (local Postgres)
- MetaMask (community form signing)

### 1. Configure `.env`

```bash
cp .env.example .env
```

**New, required for ingest:** replace the placeholder issuer addresses with real wallets. Unsigned or unknown wallets are rejected (`401` / `403`).

| Variable | What to put there |
|---|---|
| `COMMUNITY_ISSUERS` | Your MetaMask address (comma-separated if several) |
| `GOVERNMENT_ISSUERS` | The government/service wallet that will sign EMS imports |
| `DEMO_SEED` | Set to `1` to import the packaged CSVs **only when the database is empty** (dates shifted once so the series end in 2025) |
| `DATABASE_URL` | Postgres connection. Required if you want records to survive an API restart |

Leave `BLOCKCHAIN_MODE=simulated` unless you have Sepolia RPC, a testnet key, and `ETH_CONTRACT_ADDRESS` set. Mainnet anchoring is refused.

Load the file in the shells that start the services:

```bash
set -a
source .env
set +a
```

Alternatively, put `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`. The frontend already defaults to that URL.

### 2. Start Postgres

```bash
docker compose up -d db
```

Wait until `docker compose ps` shows the database as healthy.

### 3. Start the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DEMO_SEED=1 uvicorn app.main:app --reload --port 8000
```

`DATABASE_URL` from `.env` is required. The API reads and writes Postgres only; it does not keep a copy of the records in process memory. The 2019→2025 date shift runs **only on an empty database**. Later API starts query the same rows and hashes; they are not shifted again.

Check [http://localhost:8000/health](http://localhost:8000/health).

```bash
cd backend
PYTHONPATH=. pytest
```

### 4. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Do not run `npm run dev` and `npm run start` at the same time; both use the frontend `.next` directory.

### 5. Import the datasets

There is no separate import CLI. The API seeds Postgres **once**, when `water_records` is empty.

**Copy the EMS gzip** (not in git, ~364 MB) to `backend/data/this_yr.csv.gz`. The community CSV is already in the repo.

```bash
# from the repo root, after .env is loaded and Postgres is healthy
cd backend
source .venv/bin/activate
DEMO_SEED=1 uvicorn app.main:app --reload --port 8000
```

That import:

- reads `backend/app/data/dataset_download_5399.csv` (Fraser Riverkeeper / False Creek)
- streams `backend/data/this_yr.csv.gz` (shared Community↔EMS parameters, grouped into events)
- writes rows to Postgres only (the API does not keep a copy in process memory)
- shifts each series so it **ends in 2025**, only on that first empty import (original timestamps stay in `raw_payload`)

Expect on the order of **~75k records** and a couple of minutes. If the gzip is missing, the seed falls back to `backend/app/data/ems_lower_mainland.json` (a Lower Mainland extract from the same gzip).

**If the database already has rows**, the seed does nothing. Empty it and start the API again:

```bash
docker compose exec db psql -U water -d water_audit -c "TRUNCATE water_records, water_stations;"
```

Optional paths if you keep the files elsewhere:

```bash
COMMUNITY_CSV_PATH=/path/to/dataset_download_5399.csv
EMS_CSV_PATH=/path/to/this_yr.csv.gz
DEMO_END_YEAR=2025
```

Open a site on the map to see the **record hash** (fingerprint of the water data) and **on-chain** status. Simulated anchors stay labeled *Simulated locally* until a Sepolia transaction exists, then **View on explorer** opens Etherscan. **Check hashes** re-computes the stored SHA-256 hashes in the popup. **Community JSON** / **EMS JSON** open `GET /api/v1/records/{id}/verify`.

The map shows **comparison pairs** (community + EMS within 50 m) as ☺/☹ markers, plus **official EMS stations** in the Lower Mainland that have no community pair. The community CSV has three False Creek sites: Olympic Village, Brokers Bay, and Vanier Park. Volunteer Park, New Brighton, and Vanier Park Boat Ramp are not in this CSV. There is no EMS station within 50 m of False Creek, so the demo copies nearest EMS chemistry onto those three coordinates. ☺ means the two datasets match on shared parameters; ☹ means at least one value differs.

`GET /api/v1/map` is the payload the frontend uses. `GET /api/v1/records/recent` fills the list under the map. Without demo seed, community submits are stored even without a nearby EMS station, but `displayable` stays `false` until a government station exists within **50 m**. You can also `POST /api/v1/import/ems` with a signed government event.

### Production frontend build

```bash
cd frontend
npm run build
npm run start
```

## Current API

| Method | Path | Current behavior |
|---|---|---|
| `GET` | `/health` | Reports API availability |
| `POST` | `/api/v1/records` | Community ingest: signature + community issuer + 50 m station match |
| `POST` | `/api/v1/import/ems` | Government EMS event: signature + government issuer; upserts the station |
| `GET` | `/api/v1/map` | Compared False Creek pairs plus official Lower Mainland EMS stations |
| `GET` | `/api/v1/stations` | Lists government stations |
| `GET` | `/api/v1/records` | Lists displayable records; `include_unmatched=true` includes unmatched community rows |
| `GET` | `/api/v1/records/recent` | Newest ingested records for the map ledger |
| `GET` | `/api/v1/records/{id}` | Returns one record |
| `GET` | `/api/v1/records/{id}/verify` | Recalculates the content hash; includes a Sepolia transaction URL when anchored |
| `POST` | `/api/v1/records/{id}/anchor` | Runs the configured blockchain adapter |
| `POST` | `/api/v1/comparisons` | Returns neutral field-by-field differences |

Community POST bodies include `signature`, `signerAddress`, `signedContentHash`, `signatureMethod`, and optional `anchor`. Those envelope fields are not part of the content hash.

Comparison labels describe relationships only: `same_value_and_unit`, `different_value_or_unit`, `missing_from_government`, and `missing_from_community`.

## Roadmap

1. **Bulk import CLIs** — community CSV and streaming EMS CSV through the same ingest core.
2. **Durability** — replace the in-memory store with PostgreSQL or another durable database and preserve complete upstream payloads.
3. **On-chain issuer checks** — query the deployed registry `isIssuer` instead of the env allowlist.
4. **Live viewer and leaderboard** — replace remaining placeholder map/leaderboard data with API records.

## Trust boundary

Tideproof can demonstrate that a record has not changed since it was hashed and, when enabled, anchored. It can identify the registered wallet that submitted the record and preserve where the data came from.

It cannot prove that:

- every measurement was submitted;
- a sensor was calibrated correctly;
- a source is unbiased;
- a measurement is scientifically true; or
- a high contribution count makes an actor trustworthy.

Those limits should remain visible through provenance, measurement methods, comparison details, and neutral interface language.

## Governance and contributing

Read [DEV_GUIDE.md](DEV_GUIDE.md) and the [governance and regulatory guidance](governance_and_regulatory/README.md) before changing ingestion, identity, data retention, or blockchain behavior.

Do not commit credentials, private keys, `node_modules`, or generated `.next` files. Keep raw water-quality data off-chain and use clearly fake data in examples and demos.
