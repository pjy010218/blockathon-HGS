# How to use the audit trail

End to end, from nothing installed to a record anchored on Sepolia and a
contribution credited. Roughly 20 minutes the first time.

Everything runs on a testnet. No real money is involved at any point.

## What you need

| | |
| --- | --- |
| **MetaMask** | Browser extension. Install from [metamask.io](https://metamask.io) and create a wallet. |
| **Sepolia ETH** | Free test currency for transaction fees. |
| **Remix** | [remix.ethereum.org](https://remix.ethereum.org). Browser-based; nothing to install. |

## 1. Point MetaMask at Sepolia

Open MetaMask, click the network name at the top, and pick **Sepolia**. If it is
not listed, turn on **Settings → Advanced → Show test networks** first.

Your balance will read `0 SepoliaETH`. That is expected.

## 2. Get test currency

Copy your address from MetaMask (click the `0x…` at the top), then go to the
[Google Cloud Sepolia faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia),
paste it, and request. It sends 0.05 SepoliaETH. The balance appears within a
minute.

**You can only claim once per day**, so top up before you need it rather than
when you run out.

0.05 goes a long way for normal use — deploying both contracts costs about 0.005,
and each record costs about 0.0001. What burns through it is redeploying: every
edit to a `.sol` file means deploying again and re-registering issuers. Get the
contracts settled before you start deploying in earnest.

## 3. Load the contracts into Remix

Open [remix.ethereum.org](https://remix.ethereum.org), then drag
`WaterAuditRegistry.sol` and `VolunteerCredential.sol` from this directory onto
the file explorer on the left.

Open `WaterAuditRegistry.sol` and press **Compile**. Any Solidity **0.8.24 or
newer** works. Wait for the green tick.

## 4. Connect Remix to your wallet

Go to the **Deploy & Run** tab (the Ethereum diamond on the left rail) and set
**ENVIRONMENT** to `WalletConnect`, then approve the connection in MetaMask.

Check two things before going further, because everything after this depends on
them:

- **ACCOUNT** shows your own address and your real balance. If it lists several
  accounts holding 100 ETH each, you are still on `Remix VM` — a sandbox inside
  the browser that never touches Sepolia.
- The panel says **Sepolia (11155111)**.

If the connection dialog hangs on *Continue in MetaMask*, close it, unlock
MetaMask, and pick the environment again.

## 5. Deploy the registry

With `WaterAuditRegistry` selected in the **CONTRACT** dropdown, press **Deploy**
and confirm in MetaMask.

> **Read "Interacting with" in every MetaMask confirmation.** It is the only place
> the target address is shown plainly. If it is not the contract you meant, cancel.
>
> Untick **Added protection** if it appears. It routes the call through a helper
> contract, which still works but makes the Remix log show that helper as the
> recipient, which is confusing to read back.

The address appears under **Deployed Contracts**. Copy it — you need it twice more.

## 6. Register yourself as an issuer

Anchoring is restricted, so nothing can be recorded until an issuer exists. Expand
the deployed registry and call **`registerIssuer`**:

```
account   <your MetaMask address>
role      community
```

Check it took: **`issuerRole`** with your address returns
`0x636f6d6d756e69747900…` — that is `community` stored as bytes32.

## 7. Anchor a record

**`anchorRecord`**, using the sample record from `demo.py`:

```
recordHash      0xa798b33298f4554cb6e25ef411f1ce4d43e52a06a78a06e0e52eeaaad6fdd8da
source          community
sourceRecordId  swimdrinkfish-2019-06-05-1700
```

That digest is not arbitrary — it is the SHA-256 of a canonical serialization of a
real False Creek reading. To hash your own record instead:

```bash
PYTHONPATH=. .venv/bin/python -c "
from build import content_hash
print('0x' + content_hash({'station_id': 'YourStation', 'value': 7.2}))"
```

## 8. Verify it

**`getAnchor`** with the same hash returns six fields:

```
anchoredAt      the block timestamp
submitter       you — whoever sent the transaction
attributedTo    you — the contributor it belongs to
issuerRole      community
source          community
sourceRecordId  swimdrinkfish-2019-06-05-1700
```

`submitter` and `attributedTo` differ only when a service wallet relays a
submission on a contributor's behalf.

> `getAnchor` is a **`view`** function: it costs nothing, needs no wallet, and asks
> nobody's permission. That is the public lookup path.

## 9. Deploy the credential and claim

Open `VolunteerCredential.sol`, **Compile**, switch the **CONTRACT** dropdown to
`VolunteerCredential`, and paste the registry address into the field beside
**Deploy**. Deploy and confirm.

> The registry address is stored `immutable`. Get it wrong and every claim fails
> with `record is not anchored`, because the credential is reading a different
> registry.

Then call **`claimContribution`** with the same record hash, and check
**`contributionCount`** with your address. It returns `1`.

## 10. Watch it refuse things

This is the part worth demonstrating. Each of these fails, and the reason is the
point.

| Try this | What happens | Why it matters |
| --- | --- | --- |
| `claimContribution` with the same hash again | `record already credited` | One observation cannot be counted twice |
| `isAnchored` with `0x1111…1111` | `false` | A record that was never reported is visibly absent |
| `claimContribution` with `0x1111…1111` | `record is not anchored` | Credit cannot be invented from nothing |
| Change one value in the record, rehash, then `isAnchored` | `false` | An altered record no longer matches what was anchored |

A revert reaches Remix as a **Gas estimation failed** dialog naming the reason.
Nothing has been sent at that point — press **Cancel Transaction**.

## Reading the chain without Remix

Remix and MetaMask can both mislead about what actually happened. To check
independently:

```bash
cd contracts
PYTHONPATH=. .venv/bin/python - <<'PY'
from web3 import Web3
from build import compile_registry
w3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia-rpc.publicnode.com"))
registry = w3.eth.contract(
    address=Web3.to_checksum_address("0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0"),
    abi=compile_registry()[0],
)
print(registry.functions.getAnchor(bytes.fromhex("a798b33298f4554cb6e25ef411f1ce4d43e52a06a78a06e0e52eeaaad6fdd8da")).call())
PY
```

## Without a wallet at all

`demo.py` walks the same four scenarios against an EVM running inside the test
process — no MetaMask, no faucet, no network:

```bash
PYTHONPATH=. .venv/bin/pytest -q      # 40 tests
PYTHONPATH=. .venv/bin/python demo.py
```

## If you redeploy

Editing a `.sol` file makes the deployed addresses stale, and issuers must be
registered again on the new instance. Redeploy both contracts together so the
credential points at the current registry, and update the addresses in
[../README.md](../README.md).
