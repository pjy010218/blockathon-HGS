import Web3 from "web3";

declare global {
  interface Window {
    ethereum?: { request: (args: { method: string }) => Promise<unknown> };
  }
}

export const WATER_AUDIT_REGISTRY_ABI = [
  {
    inputs: [{ name: "recordHash", type: "bytes32" }],
    name: "getAnchor",
    outputs: [
      { name: "anchoredAt", type: "uint64" },
      { name: "submitter", type: "address" },
      { name: "source", type: "string" },
      { name: "sourceRecordId", type: "string" },
    ],
    stateMutability: "view",
    type: "function",
  },
] as const;

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
