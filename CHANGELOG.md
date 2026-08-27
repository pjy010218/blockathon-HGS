# Changelog

Quick, chronological summaries of meaningful project changes. Implementation details belong in pull requests and technical specifications.

## 2026-08-27 — Live frontend data

- Connected the Map to display station-matched government and community comparisons from the API.
- Connected the Leaderboard to accepted, issuer-signed community contribution records.
- Added clear loading, unavailable, and empty-data states for both live views.

## 2026-08-27 — Signed ingress and station matching

- Community `POST /api/v1/records` now requires an EIP-191 signature and a community issuer wallet.
- Added `POST /api/v1/import/ems` for signed government events, `GET /api/v1/stations`, and 50 m station matching.
- Unmatched community records stay stored but are hidden from the default record list.

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
