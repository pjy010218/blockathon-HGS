# Water Audit Trail

An SDG 14 project for making water-quality data changes detectable while leaving interpretation to the reader.

## Purpose

Government, industrial, and community water data can differ. This project does not assign a trust score, select a preferred source, or tell users which record to believe. It preserves the source identity, original payload, provenance, and field-level differences so readers can inspect the evidence themselves.

Each ingested record is normalized for comparison and hashed using deterministic JSON. The hash can be anchored to Ethereum through `WaterAuditRegistry.sol`. The raw data remains off-chain so it can be queried and compared without putting large payloads on-chain.

## Repository structure

```text
backend/
  app/main.py                 FastAPI routes and in-memory MVP store
  app/models/schemas.py       Provenance, measurement, comparison, and anchor models
  app/services/hashing.py     Deterministic SHA-256 content hashing
  app/services/comparison.py  Neutral field-by-field comparison
  app/services/blockchain.py  Ethereum adapter boundary; simulated locally by default
  tests/test_api.py            API and missing-field behavior tests
frontend/
  app/                        Next.js viewer
  components/                 Source record cards
  lib/                        API client and shared types
contracts/
  WaterAuditRegistry.sol      Minimal Ethereum hash registry
```

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run tests with:

```bash
PYTHONPATH=. pytest
```

### Frontend

Node.js 20+ is recommended.

```bash
cd frontend
npm install
npm run dev
```

The UI expects the API at `http://localhost:8000`; override it with `NEXT_PUBLIC_API_URL`.

## API backbone

- `POST /api/v1/records` ingests a source-preserving record and computes its hash.
- `GET /api/v1/records` lists records without merging away source differences.
- `GET /api/v1/records/{id}/verify` recalculates the hash and reports whether it matches.
- `POST /api/v1/records/{id}/anchor` invokes the blockchain adapter. Local mode is explicitly labeled `simulated`.
- `POST /api/v1/comparisons` compares one government record with one community record field by field.

Comparison statuses are deliberately descriptive: `same_value_and_unit`, `different_value_or_unit`, `missing_from_government`, and `missing_from_community`. Missing fields are never converted to zero, null-equivalent equality, or a trust judgment.

## Data-source adapters to add next

1. Add an EnMoDS/BC Data Catalogue adapter that stores the upstream URL, dataset identifier, retrieval timestamp, and original row payload.
2. Add a DataStream/Water Rangers adapter using their open API and retain the upstream dataset/version identifiers.
3. Map source fields into canonical fields without deleting unmapped fields; keep the original payload in `raw_payload`.
4. Replace the simulated blockchain service with a Web3 transaction adapter that calls `anchorRecord(bytes32,string,string)` and stores the transaction hash.
5. Move the in-memory record store to PostgreSQL or another durable store before deployment.

## Trust boundary

The system can show that a submitted record has or has not changed since it was hashed and anchored. It cannot prove that a source submitted every measurement, that a sensor was calibrated, or that a reading is true. Those facts should remain visible as provenance and quality-control metadata for the reader to assess.
