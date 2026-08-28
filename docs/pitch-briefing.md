# Tideproof pitch briefing

Cheat sheet for the Blockathon pitch and technical Q&A. Runtime setup stays in the root `README.md`. Do not commit `.env`.

## One-sentence pitch

Tideproof hashes community and BC EMS water readings, compares them on a map, and can pin the hash to Sepolia so later edits are detectable. An on-chain hash proves the record did not change. It does not prove the measurement is true.

## What to demo

1. Map at http://localhost:3000 — ☺ match, ☹ needs review, small navy dots = official EMS with no community pair.
2. Click a face: Record hash vs on-chain status, **Check hashes**, **Proof JSON**.
3. Latest 10 hashed records under the map. Real Sepolia rows show **Explorer**; simulated rows show **Simulated locally**.
4. Data tab: pick a station (coords fill in), connect MetaMask, optional **Request blockchain anchor**, sign and submit.
5. Open Proof JSON for a live Sepolia submit and the Etherscan link.

If the map is empty, the API on port 8000 is down. Reload after it is back.

## What is running

| Piece | Role |
|---|---|
| Next.js (`frontend`, port 3000) | Map, Data form, leaderboard placeholder |
| FastAPI (`backend`, port 8000) | Signatures, issuer check, 50 m match, hash, Postgres, optional chain write |
| Postgres 16 (`docker compose db`) | Durable store. The API does not keep the 74k records in RAM |
| WaterAuditRegistry on Sepolia | `0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0` |

Uvicorn does **not** load `.env` by itself:

```bash
set -a && source .env && set +a
cd backend
source .venv/bin/activate
DEMO_SEED=1 uvicorn app.main:app --reload --port 8000
```

Postgres first: `docker compose up -d db`. Frontend: `cd frontend && npm run dev`.

## Data on the map

Import happens once, when `water_records` is empty and `DEMO_SEED=1`. Dates shift so the series end in 2025. Later starts reuse the same rows and hashes.

| Source | File | Notes |
|---|---|---|
| Community CSV | `backend/app/data/dataset_download_5399.csv` (in git) | Fraser Riverkeeper / False Creek: Olympic Village, Brokers Bay, Vanier Park |
| EMS gzip | `backend/data/this_yr.csv.gz` (~364 MB, **not** in git) | ~74k events, ~3420 stations |
| Fallback | `backend/app/data/ems_lower_mainland.json` | Lower Mainland extract if the gzip is missing |

Volunteer Park, New Brighton, and Vanier Park Boat Ramp are **not** in the community CSV. Do not invent them.

There is no EMS station within 50 m of False Creek. The seed copies nearest EMS chemistry onto those three community coordinates so the matcher can show pairs. Original EMS coordinates stay on the official navy dots.

A community submit is stored even without a nearby station, but it stays off the default map (`displayable=false`) until a government station is within 50 m.

## ☺ vs ☹

The API compares the latest community record and the latest EMS record at the same matched station.

- ☺ match: every shared parameter has the same value and an equivalent unit.
- ☹ review: at least one shared parameter differs in value or unit.
- A field present on only one side is **not** treated as a mismatch.
- `pH` (form) and `pH units` (EMS) are the same unit. A 7.1 vs 7.1 pair is a match.
- The popup shows numbers only. Units live on the stored measurements.

## Hash, Proof JSON, chain

The content hash is SHA-256 of a canonical JSON payload: source, observed_at, location, measurements, metadata, raw_payload. Station-match fields sit **outside** the hash so a record can be rematched later without changing the digest.

| Control | What it is |
|---|---|
| Record hash | Fingerprint of that payload |
| Check hashes | API re-hashes the stored row and compares it to `content_hash` |
| Proof JSON | Raw `GET /api/v1/records/{id}/verify`: `stored_hash`, `recalculated_hash`, `matches`, `anchor`, `transaction_url` |
| Simulated locally | Hash stored; a fake `0x…` receipt. **No** Etherscan link |
| View on explorer / Explorer | Real Sepolia tx. Only if `anchor.status == anchored` and network contains `sepolia` |

Proof JSON is the shareable integrity receipt. If `matches` is false, the row changed after it was hashed.

The import is simulated on purpose. Sending ~74k Sepolia transactions would drain the faucet and stall the demo.

Live Sepolia examples (community form + **Request blockchain anchor**):

- RCHMND LULU IS PE233 AT FINAL DISCHARGE — https://sepolia.etherscan.io/tx/0x191b6250fba0d61ac5b07b3a19a939a8565a022e356aa18bc4207e429429248a
- PE-7171 TRANS MOUNTAIN TREATED STORM WATER — https://sepolia.etherscan.io/tx/0x77389dd3eb9ddce10688343479b6c65488c1f26aa087cd592f19b913573078d9

`POST /api/v1/records/{id}/anchor` skips rows that are already `simulated` or `anchored`. You cannot “upgrade” an imported simulated hash to Sepolia with that button. A new Data-tab submit with the checkbox is the path for a live tx.

## Env (names only, no secrets)

| Variable | Meaning |
|---|---|
| `BLOCKCHAIN_MODE` | `simulated` (default) or `ethereum` |
| `BLOCKCHAIN_NETWORK` | e.g. `sepolia` when writing to testnet |
| `ETH_RPC_URL` | Sepolia RPC (Infura or publicnode: both chain id 11155111) |
| `ETH_PRIVATE_KEY` | Relayer **wallet** secret, not an API key. Never commit |
| `ETH_CONTRACT_ADDRESS` | WaterAuditRegistry, see `.env.example` |
| `COMMUNITY_ISSUERS` | MetaMask address allowlist. Empty → `403 This wallet is not registered as a community issuer.` |
| `GOVERNMENT_ISSUERS` | Wallet that may sign EMS import |
| `DATABASE_URL` | Required for persistence |
| `CORS_ORIGINS` | Include `http://localhost:3000` |

Mainnet anchoring is refused. Issuer check is still the env allowlist, not on-chain `isIssuer`.

## Likely questions

**Why only three community faces at first?**  
Those are the unique sites in the Riverkeeper CSV. Extra names from Swim Drink Fish are not in that file.

**Why so many small blue dots?**  
Official Lower Mainland EMS stations with no community pair inside 50 m.

**Did you put everything on the blockchain?**  
No. Import is hashed in Postgres with a simulated receipt. Two community submits are on Sepolia. The hash that would go on-chain is the same SHA-256 Proof JSON recomputes.

**What does the wallet signature prove?**  
The MetaMask account signed that content hash. The API recovers the signer and checks `COMMUNITY_ISSUERS`. That is identity of the submitter, not correctness of pH.

**What does the contract store?**  
The digest, source label, source record id, issuer role, timestamp. Not the raw chemistry. See `contracts/README.md`.

**Could someone edit the database and hide it?**  
Check hashes / Proof JSON would show `matches: false`. If the hash was anchored, the chain still has the original digest.

**Why was a site red when pH looked the same?**  
The comparator used to require the unit strings to be identical (`pH` vs `pH units`). That alias is now accepted.

**Leaderboard?**  
Placeholder UI. Rankings are not computed from accepted records yet.

## Do not

- Re-run `DEMO_SEED=1` with `BLOCKCHAIN_MODE=ethereum` on a full database (or after `TRUNCATE`) unless you intend tens of thousands of testnet txs.
- Invent community stations that are not in the CSV.
- Commit `.env`, private keys, or `this_yr.csv.gz`.
- Claim an on-chain hash means the water reading is accurate.
