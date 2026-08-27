# Align Clients With WaterAuditRegistry

> Inline execution. No git commit unless requested.

**Goal:** Make frontend and backend speak the live `WaterAuditRegistry` ABI (6-field Anchor tuple, issuer roles, relayer `attributedTo`).

**Architecture:** Solidity stays as-is. Clients adopt the contract ABI. Simulated anchoring remains the default; `BLOCKCHAIN_MODE=ethereum` sends `anchorRecord` / `anchorRecordFor` on testnet only.

**Tech Stack:** Solidity 0.8.24 (unchanged), FastAPI + web3.py 7, Next.js `frontend/lib/blockchain.ts`.

## Comparison (locked)

| Surface | Spec / Solidity | Current client | Action |
|---|---|---|---|
| `registerIssuer` / `revokeIssuer` / `isIssuer` | On-chain, owner-only, roles `community` \| `government` | Not used by API/UI | No Solidity change |
| `anchorRecord` | Caller must be registered issuer | Backend simulated only | Wire ethereum mode |
| `anchorRecordFor` | Relayer = `submitter`, signer = `attributedTo` | Missing | Use when `attributed_to` passed |
| `getAnchor` | One `tuple` of 6 fields | Frontend ABI: 4 flat outputs | Fix ABI |
| VolunteerCredential `IWaterAuditRegistry.Anchor` | Mirrors registry | In sync | None |

Public `isIssuer(address,string)` vs spec `bytes32` is an intentional string wrapper; stored role is still `bytes32`.

---

### Task 1: Frontend ABI

- Replace flattened `getAnchor` outputs with the tuple + `isAnchored` / `getAnchors`.
- Helpers: bytes32 hash, treat `anchoredAt === 0` as unknown.

### Task 2: Backend adapter

- Simulated default unchanged.
- Ethereum mode: env `ETH_RPC_URL`, `ETH_PRIVATE_KEY`, `ETH_CONTRACT_ADDRESS`; refuse chain id 1.
- `anchor(hash, source, source_record_id, attributed_to=None)`.

### Task 3: Tests + env docs

- Hash → bytes32 tests; simulated vs unconfigured ethereum; mocked transact.
- `.env.example` documents ethereum vars without real keys.
