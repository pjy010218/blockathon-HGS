import { WATER_QUALITY_PARAMETERS } from "./water-quality-schema";

export type CanonicalMeasurement = {
  field: string;
  value: number;
  unit: string;
  raw_value: string;
  method: string;
};

export type CommunityRecordCreate = {
  source: {
    kind: "community";
    provider: string;
    dataset_id: string;
    source_record_id: null;
    source_url: null;
    retrieved_at: null;
  };
  observed_at: string;
  location: {
    name: string;
    latitude: number;
    longitude: number;
  };
  measurements: CanonicalMeasurement[];
  metadata: {
    medium: string;
    collection_method: string;
  };
  raw_payload: Record<string, string>;
};

export type SignedCommunitySubmission = CommunityRecordCreate & {
  signature: string;
  signerAddress: string;
  signedContentHash: string;
  signatureMethod: "personal_sign";
  anchor: boolean;
};

export type WalletProvider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
};

function sortForCanonicalJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortForCanonicalJson);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
        .map(([key, entry]) => [key, sortForCanonicalJson(entry)]),
    );
  }
  return value;
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortForCanonicalJson(value));
}

export async function sha256Hex(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function buildCommunityRecord(form: FormData): CommunityRecordCreate {
  const siteName = requiredString(form, "site");
  const observedAtInput = requiredString(form, "sampledAt");
  const medium = requiredString(form, "medium");
  const collectionMethod = requiredString(form, "method");
  const latitude = requiredCoordinate(form, "latitude", -90, 90);
  const longitude = requiredCoordinate(form, "longitude", -180, 180);
  const observedAt = new Date(observedAtInput);

  if (Number.isNaN(observedAt.getTime())) throw new Error("Enter a valid sampling date and time.");

  const rawPayload: Record<string, string> = {
    site: siteName,
    observed_at_local: observedAtInput,
    medium,
    collection_method: collectionMethod,
    latitude: String(form.get("latitude") ?? ""),
    longitude: String(form.get("longitude") ?? ""),
  };
  const measurements = WATER_QUALITY_PARAMETERS.flatMap<CanonicalMeasurement>((parameter) => {
    const rawValue = String(form.get(parameter.key) ?? "").trim();
    if (!rawValue) return [];
    const value = Number(rawValue);
    if (!Number.isFinite(value)) throw new Error(`${parameter.label} must be a number.`);
    rawPayload[parameter.communityField] = rawValue;
    return [{ field: parameter.key, value, unit: parameter.unit, raw_value: rawValue, method: collectionMethod }];
  });

  if (measurements.length === 0) throw new Error("Enter at least one water-quality measurement.");

  const notes = String(form.get("notes") ?? "").trim();
  if (notes) rawPayload.field_notes = notes;

  return {
    source: {
      kind: "community",
      provider: "Tideproof community form",
      dataset_id: "community-form-v1",
      source_record_id: null,
      source_url: null,
      retrieved_at: null,
    },
    observed_at: observedAt.toISOString().replace(".000Z", "Z"),
    location: { name: siteName, latitude, longitude },
    measurements,
    metadata: { medium, collection_method: collectionMethod },
    raw_payload: rawPayload,
  };
}

export async function signCommunityRecord(
  record: CommunityRecordCreate,
  signerAddress: string,
  provider: WalletProvider,
  anchor: boolean,
): Promise<SignedCommunitySubmission> {
  const contentHash = await sha256Hex(record);
  const signature = await provider.request({
    method: "personal_sign",
    params: [`0x${contentHash}`, signerAddress],
  });

  if (typeof signature !== "string") throw new Error("MetaMask did not return a signature.");

  return {
    ...record,
    signature,
    signerAddress,
    signedContentHash: contentHash,
    signatureMethod: "personal_sign",
    anchor,
  };
}

function requiredString(form: FormData, name: string): string {
  const value = String(form.get(name) ?? "").trim();
  if (!value) throw new Error(`Complete the ${name === "sampledAt" ? "sampling time" : name} field.`);
  return value;
}

function requiredCoordinate(form: FormData, name: "latitude" | "longitude", min: number, max: number): number {
  const rawValue = requiredString(form, name);
  const value = Number(rawValue);
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new Error(`${name[0].toUpperCase()}${name.slice(1)} must be between ${min} and ${max}.`);
  }
  return value;
}
