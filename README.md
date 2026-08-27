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

Leave `BLOCKCHAIN_MODE=simulated` unless you have Sepolia RPC, a testnet key, and `ETH_CONTRACT_ADDRESS` set. Mainnet anchoring is refused.

Load the file in the shells that start the services:

```bash
set -a
source .env
set +a
```

Alternatively, put `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`. The frontend already defaults to that URL.

### 2. Start the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check [http://localhost:8000/health](http://localhost:8000/health).

```bash
cd backend
PYTHONPATH=. pytest
```

### 3. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Do not run `npm run dev` and `npm run start` at the same time; both use the frontend `.next` directory.

### 4. Optional: seed a government station

Community submits are stored even without a nearby EMS station, but `displayable` stays `false` and they stay off the default record list until a government station exists within **50 m**.

Sign an EMS event with the government issuer key and `POST /api/v1/import/ems` (see Current API). After that, `GET /api/v1/stations` fills the form datalist, and a community reading at those coordinates can match.

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
| `GET` | `/api/v1/stations` | Lists government stations |
| `GET` | `/api/v1/records` | Lists displayable records; `include_unmatched=true` includes unmatched community rows |
| `GET` | `/api/v1/records/{id}` | Returns one record |
| `GET` | `/api/v1/records/{id}/verify` | Recalculates and compares its content hash |
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
