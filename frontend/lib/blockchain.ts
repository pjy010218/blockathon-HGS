import Web3 from "web3";

declare global {
  interface Window {
    ethereum?: { request: (args: { method: string }) => Promise<unknown> };
  }
}

/** Sepolia WaterAuditRegistry (see contracts/README.md). */
export const WATER_AUDIT_REGISTRY_ADDRESS =
  "0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0" as const;

const ANCHOR_COMPONENTS = [
  { name: "anchoredAt", type: "uint64" },
  { name: "submitter", type: "address" },
  { name: "attributedTo", type: "address" },
  { name: "issuerRole", type: "bytes32" },
  { name: "source", type: "string" },
  { name: "sourceRecordId", type: "string" },
] as const;

/**
 * ABI for the live registry. `getAnchor` is one tuple, not four/six flat
 * outputs — a flattened ABI decodes the return data incorrectly.
 */
export const WATER_AUDIT_REGISTRY_ABI = [
  {
    inputs: [{ name: "recordHash", type: "bytes32" }],
    name: "getAnchor",
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [...ANCHOR_COMPONENTS],
      },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "recordHash", type: "bytes32" }],
    name: "isAnchored",
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ name: "recordHashes", type: "bytes32[]" }],
    name: "getAnchors",
    outputs: [
      {
        name: "",
        type: "tuple[]",
        components: [...ANCHOR_COMPONENTS],
      },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { name: "account", type: "address" },
      { name: "role", type: "string" },
    ],
    name: "isIssuer",
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "view",
    type: "function",
  },
] as const;

export type RegistryAnchor = {
  anchoredAt: bigint | number | string;
  submitter: string;
  attributedTo: string;
  issuerRole: string;
  source: string;
  sourceRecordId: string;
};

export function contentHashToBytes32(contentHash: string): string {
  const hex = contentHash.replace(/^0x/i, "");
  if (hex.length !== 64) {
    throw new Error(`A record hash must be 32 bytes; got ${hex.length / 2}`);
  }
  return `0x${hex}`;
}

/** `getAnchor` returns a zeroed struct for unknown hashes — not an error. */
export function isPresentAnchor(anchor: RegistryAnchor): boolean {
  return BigInt(anchor.anchoredAt) !== BigInt(0);
}

export function getRegistry(web3: Web3, address: string = WATER_AUDIT_REGISTRY_ADDRESS) {
  return new web3.eth.Contract(WATER_AUDIT_REGISTRY_ABI, address);
}

export async function connectWallet(): Promise<string> {
  if (!window.ethereum) throw new Error("An Ethereum wallet was not found");
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  if (!Array.isArray(accounts) || typeof accounts[0] !== "string") {
    throw new Error("No Ethereum account was provided");
  }
  return accounts[0];
}

export function getWeb3(): Web3 {
  if (!window.ethereum) throw new Error("An Ethereum wallet was not found");
  return new Web3(window.ethereum as never);
}
