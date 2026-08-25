import type { ComparisonResponse, WaterQualityRecord } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function listRecords(): Promise<WaterQualityRecord[]> {
  const response = await fetch(`${API_URL}/api/v1/records`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load records");
  return response.json();
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
