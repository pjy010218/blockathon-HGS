# Changelog

Quick, chronological summaries of meaningful project changes. Implementation details belong in pull requests and technical specifications.

## 2026-08-27 — Full EMS gzip import

- Demo seed now streams `this_yr.csv.gz` into Postgres (shared parameters, grouped events). The gzip stays local and is gitignored.
- The map loads only community records plus the paired government rows, not the full EMS table.

## 2026-08-27 — Postgres persistence and map proofs

- Initial CSV import writes records and stations to Postgres when `DATABASE_URL` is set.
- Dates are shifted to end in 2025 only while the database is empty; later boots reload the same hashes.
- Each imported record gets a simulated hash proof. The map popup can re-check it against `GET /api/v1/records/{id}/verify`.

## 2026-08-27 — Real CSV demo with 2025 dates

- Demo seed now imports the Fraser Riverkeeper community CSV and a compact Lower Mainland EMS sample instead of eight synthetic pairs.
- Observation dates are shifted so each series ends in 2025; original timestamps remain in `raw_payload`.
- The large EMS gzip is not in git. False Creek sites are paired by copying nearest EMS chemistry onto community coordinates (the 50 m matcher has no real EMS station there).

## 2026-08-27 — Signed ingress and station matching

- Community `POST /api/v1/records` now requires an EIP-191 signature and a community issuer wallet.
- Added `POST /api/v1/import/ems` for signed government events, `GET /api/v1/stations`, and 50 m station matching.
- Unmatched community records stay stored but are hidden from the default record list.
- Community CSV adapter, demo seed (`DEMO_SEED=1`), and map comparisons from imported pairs.

## 2026-08-27 — Registry client alignment

- Matched the frontend `getAnchor` ABI to the six-field on-chain Anchor tuple.
- Added a backend Ethereum adapter for `WaterAuditRegistry` (`BLOCKCHAIN_MODE=ethereum`, testnet only). Simulated anchoring remains the default.

## 2026-08-27 — Frontend integration readiness

- Introduced the Tideproof frontend with Map, Data, and Leaderboard views.
- Added an interactive Vancouver-area water-quality comparison map with prototype match and review markers.
- Added a community contribution journey with wallet connection, signed submissions, optional anchoring, and clear result states.
- Aligned community submission and map comparisons around the shared Community and EMS water-quality parameters.
- Added station-directory and station-matching placeholders for backend integration.
- Clarified that contributor identity and contribution history do not prove that a measurement is true.
- Added responsive layouts, mobile navigation, keyboard focus states, and reduced-motion support.
- Documented the planned dual-ingress architecture for community and government data.

## 2026-08-25 — Project foundation

- Established the Water Audit Trail project and its SDG 14 purpose.
- Added source-preserving water-quality records and neutral record comparisons.
- Added deterministic record hashing and record-integrity verification.
- Added a simulated blockchain anchoring path and initial Ethereum registry contract.
- Added initial community and government data-adapter boundaries.
- Added governance and regulatory guidance for future development.

