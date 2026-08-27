# Contracts

| Contract | Purpose |
| --- | --- |
| `WaterAuditRegistry.sol` | Records that a record digest existed at a time, who submitted it, and under which issuer role. |
| `VolunteerCredential.sol` | Recognises that an address anchored records. Not tradeable, no issuer. |

An anchor proves a digest existed and has not changed since. It does not prove the
measurement is accurate.

New to this? [docs/how-to-start.md](docs/how-to-start.md) walks the whole thing end
to end, from installing MetaMask to a credited contribution.

## Setup

```bash
cd contracts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Test

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Runs against an in-process EVM — no RPC, key, or faucet. `solc` downloads on first
compile.

## Compile and deploy

```bash
PYTHONPATH=. .venv/bin/python build.py [VolunteerCredential]    # print an ABI

export ETH_RPC_URL=... ETH_PRIVATE_KEY=...      # testnet only, never committed
.venv/bin/python deploy.py --dry-run
.venv/bin/python deploy.py
.venv/bin/python deploy.py --contract VolunteerCredential --registry 0x...
```

Mainnet is refused.

## Demo

```bash
PYTHONPATH=. .venv/bin/python demo.py
```

Submit, verify, tamper, and not-reported, using only the contracts — no backend
or frontend needed. Runs on an in-process EVM unless `ETH_RPC_URL`,
`ETH_PRIVATE_KEY`, and `ETH_CONTRACT_ADDRESS` point it at a deployed contract.

## Lookup

All view functions: no wallet, no gas, nothing granted.

| Function | Use |
| --- | --- |
| `isAnchored(bytes32)` | Is this record on-chain? |
| `getAnchor(bytes32)` | When, by whom, which source. |
| `getAnchors(bytes32[])` | A screenful of map pins in one call. |
| `isIssuer(address, string)` | Is this account allowed to submit under that role? |
| `issuerRole(address)` | Which role an account holds, if any. |

## Gotchas

- `getAnchor` returns a zeroed struct for an unknown hash, and `0x0000…` reads like
  a real submitter. Check `anchoredAt != 0`, or use `isAnchored`.
- A chain lookup proves *a* digest was anchored. Recompute the hash from the record
  on screen too, or it proves nothing about the data shown.
- The digest covers serialization, not meaning. A renamed field, an added empty
  field, or a changed timestamp format moves the hash with no data change, so a
  mismatch is ambiguous unless the canonical form is versioned. Put the version in
  `source` (`enmods@2026-08-26`).
- Keep something unique per record inside the hashed content (`source_record_id`).
  Without it two identical observations collide and the second anchor reverts.
- Anchor at ingestion, filter at presentation. Filtering first makes the chain
  attest to a curated subset. `anchorRecords` batches a run (~75k vs ~96k gas per
  record, ~400 per block), so cost is not a reason to filter first.
- Only `recordHash`, `submitter`, and `attributedTo` are indexed. Finding anchors
  by location or source needs an off-chain index.

## Issuers and credit

Anchoring is restricted to accounts the owner has registered under the role
`community` or `government`, so one source cannot be passed off as the other.
`registerIssuer` and `isIssuer` take the role by name; the published constants
show how a name is stored. The role in force at anchoring time is kept on the
record, so revoking an issuer later never rewrites what a past record says.

This is a trade the import interface spec asks for: the registry now has an
**owner** who decides who may submit and can revoke them. Question 11 in
[../governance_and_regulatory/checklist.md](../governance_and_regulatory/checklist.md)
must name that key holder — it is a real control point, and "nobody can
intervene" is no longer the answer.

An anchor records two addresses. `submitter` is whoever sent the transaction;
`attributedTo` is the contributor it belongs to. `anchorRecordFor` lets a service
wallet relay a submission after verifying the contributor's signature off-chain,
so credit follows the signer rather than whoever paid the gas.
`claimContribution` reads `attributedTo`, and only the caller can claim their own
records — contributing and being counted stay separate decisions.

The credential itself has no token, no supply, no price, and no transfer path, so
checklist question 1 stays answered "No".

## Deployed

Sepolia (chain id 11155111), verified on Sourcify and Blockscout:

| Contract | Address |
| --- | --- |
| `WaterAuditRegistry` | `0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0` |
| `VolunteerCredential` | `0x700B8E4ab00c6573911C219E1B74dABc66bdcdE9` |

Owner and `community` issuer: `0x74D96FF3dc16AeE3d5342DE17E084f9DBA4B77D5`.
Earlier deployments predate the issuer registry and are dead.

## For backend and frontend

Everything a client needs to read the chain. Nothing here requires a wallet — all
three lookups are `view` calls, so a public Sepolia RPC endpoint is enough. Take
the addresses and chain id from [Deployed](#deployed) above.

Generate the ABI rather than hand-writing it:

```bash
PYTHONPATH=. .venv/bin/python build.py > registry.abi.json
PYTHONPATH=. .venv/bin/python build.py VolunteerCredential > credential.abi.json
```

Two things a client must get right:

- **`getAnchor` and `getAnchors` return a struct, not separate values.** The ABI
  entry has one output of type `tuple` with six components. Declaring six flat
  outputs decodes the return data incorrectly. `frontend/lib/blockchain.ts`
  currently does exactly that and needs the tuple form.
- **An unknown hash returns a zeroed struct, not an error.** Check
  `anchoredAt != 0`, or call `isAnchored` first, before showing any other field —
  otherwise `0x0000…` renders as a real submitter.

## TODO

- [ ] Decide who holds the owner key, and record it in the governance checklist

Not ours to fix, but worth flagging: `frontend/lib/blockchain.ts` declares
`getAnchor` with four flat outputs instead of one struct, so it decodes wrong, and
`backend/app/services/blockchain.py` is still simulated.

## Rules

- An anchor is never modifiable. A correction is a new anchor.
- No owner, upgrade, pause, or fee without a stated reason — "nobody can intervene"
  is worth keeping.
- Never add a transfer, price, or reward path to the credential.
- No personal data on-chain. No keys or `.env` in git.
- `camelCase` functions, `PascalCase` types, `UPPER_SNAKE_CASE` constants.
- Contract changes reviewed separately (`DEV_GUIDE.md` §7).
- A test for every new state or revert path.
