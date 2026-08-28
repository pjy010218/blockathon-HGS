import type { SignedCommunitySubmission } from "./community-submission";
import type { ComparisonResponse, GovernmentStation, MapSite, RecentRecord, WaterQualityRecord } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export async function listRecords(): Promise<WaterQualityRecord[]> {
  const response = await fetch(`${API_URL}/api/v1/records`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load records");
  return response.json();
}

export async function listStations(): Promise<GovernmentStation[]> {
  const response = await fetch(`${API_URL}/api/v1/stations`, { cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, "Station directory is not available yet");
  return response.json();
}

export async function listMapSites(): Promise<MapSite[]> {
  const response = await fetch(`${API_URL}/api/v1/map`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load map comparisons");
  return response.json();
}

export async function listRecentRecords(limit = 10): Promise<RecentRecord[]> {
  const response = await fetch(`${API_URL}/api/v1/records/recent?limit=${limit}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load recent records");
  return response.json();
}

export async function verifyRecord(recordId: string): Promise<{
  record_id: string;
  stored_hash: string;
  recalculated_hash: string;
  matches: boolean;
  anchor: WaterQualityRecord["blockchain"];
  transaction_url?: string | null;
}> {
  const response = await fetch(`${API_URL}/api/v1/records/${recordId}/verify`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to verify this record");
  return response.json();
}

export async function submitCommunityRecord(payload: SignedCommunitySubmission): Promise<WaterQualityRecord> {
  const response = await fetch(`${API_URL}/api/v1/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(response.status, body?.detail ?? submissionErrorMessage(response.status));
  }
  return response.json();
}

function submissionErrorMessage(status: number): string {
  if (status === 400) return "The signed record did not match the submitted record.";
  if (status === 401) return "MetaMask signature verification failed.";
  if (status === 403) return "This wallet is not registered as a community issuer.";
  if (status === 409) return "This exact record has already been submitted.";
  return "The record could not be submitted. Check the API connection and try again.";
}

export async function compareRecords(
  governmentRecordId: string,
  communityRecordId: string,
): Promise<ComparisonResponse> {
  const response = await fetch(`${API_URL}/api/v1/comparisons`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      government_record_id: governmentRecordId,
      community_record_id: communityRecordId,
    }),
  });
  if (!response.ok) throw new Error("Unable to compare records");
  return response.json();
}
