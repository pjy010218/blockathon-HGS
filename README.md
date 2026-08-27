# Tideproof — Water Audit Trail

Tideproof is an SDG 14 project for preserving and comparing community and government water-quality records in British Columbia. It makes changes detectable, keeps provenance visible, and lets readers inspect differences without declaring which source is correct.

The project combines a public-facing Next.js application, a FastAPI ingestion and comparison service, and an Ethereum record-hash registry.

## Project status

Tideproof is currently a hackathon prototype with a production-oriented integration design.

| Area | Available now | Planned next |
|---|---|---|
| Map | Interactive Vancouver-area map with clearly labeled prototype comparisons | Load only station-matched records and comparisons from the API |
| Community data | Canonical form, client-side content hash, MetaMask signature, submission states, and optional anchor request | Backend signature verification, issuer authorization, station matching, and durable storage |
| Stations | Frontend integration boundary and graceful unavailable state | Government station registry and `GET /api/v1/stations` |
| Leaderboard | Responsive placeholder contribution history | Rankings calculated from accepted, issuer-signed records |
| API | Record creation, listing, lookup, verification, neutral comparison, and simulated anchoring | Dual community/EMS ingress, signatures, issuer roles, station matching, and unmatched filtering |
| Blockchain | Minimal record-hash registry and simulated local adapter | Registered issuer roles, restricted anchoring, and an explicit relayer model |

The frontend is ahead of several backend capabilities. It prepares and signs the intended submission envelope, but the current API does not yet enforce signatures, issuer roles, station matching, or the optional anchor flag.

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

### Requirements

- Node.js 20 or newer
- Python 3.11 or newer
- MetaMask for the wallet interaction

### Environment

Copy the example configuration and adjust it if your ports differ:

```bash
cp .env.example .env
set -a
source .env
set +a
```

Run the services from that shell so the variables are available to both processes. Alternatively, place frontend variables in `frontend/.env.local`. The frontend defaults to `http://localhost:8000` when `NEXT_PUBLIC_API_URL` is not set, and the backend allows `http://localhost:3000` by default through `CORS_ORIGINS`.

### Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run backend tests:

```bash
cd backend
PYTHONPATH=. pytest
```

### Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Create a production build with:

```bash
cd frontend
npm run build
npm run start
```

Do not run the development server and production build simultaneously because both use the frontend `.next` directory.

## Current API

| Method | Path | Current behavior |
|---|---|---|
| `GET` | `/health` | Reports API availability |
| `POST` | `/api/v1/records` | Validates, stores, and hashes a record |
| `GET` | `/api/v1/records` | Lists all in-memory records |
| `GET` | `/api/v1/records/{id}` | Returns one record |
| `GET` | `/api/v1/records/{id}/verify` | Recalculates and compares its content hash |
| `POST` | `/api/v1/records/{id}/anchor` | Runs the configured blockchain adapter |
| `POST` | `/api/v1/comparisons` | Returns neutral field-by-field differences |

Comparison labels describe relationships only: `same_value_and_unit`, `different_value_or_unit`, `missing_from_government`, and `missing_from_community`.

### Planned API additions

| Method | Path | Intended behavior |
|---|---|---|
| `POST` | `/api/v1/records` | Require a community issuer signature and run station matching |
| `POST` | `/api/v1/import/ems` | Normalize and ingest a signed government EMS event |
| `GET` | `/api/v1/stations` | Provide government station context to the community form |
| `GET` | `/api/v1/records?include_unmatched=true` | Include unmatched community records for debugging or demos |

## Roadmap

1. **Secure community ingress** — agree on cross-language canonical serialization, verify wallet signatures, enforce community issuer roles, and return actionable errors.
2. **Station-aware records** — add the station registry, 50-metre community matching, match metadata, and default viewer filtering.
3. **Government ingress** — add streaming EMS import and signed daily REST pushes through the same canonical ingestion core.
4. **Durability** — replace the in-memory store with PostgreSQL or another durable database and preserve complete upstream payloads.
5. **Blockchain roles** — register and revoke community/government issuers, restrict anchoring, and document direct-wallet versus relayer behavior.
6. **Live viewer and leaderboard** — replace all placeholder records with API data and calculate contribution history from accepted submissions.

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
