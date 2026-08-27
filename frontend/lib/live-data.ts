import { compareRecords } from "./api";
import type { MapMarkerData } from "../components/WaterMap";
import type { ComparisonField, WaterQualityRecord } from "./types";
import { WATER_QUALITY_PARAMETERS } from "./water-quality-schema";

export type ContributorSummary = {
  rank: number;
  name: string;
  handle: string;
  records: number;
  streak: string;
  place: string;
  avatar: string;
};

type StationRecords = {
  government: WaterQualityRecord[];
  community: WaterQualityRecord[];
};

export async function buildMapMarkers(records: WaterQualityRecord[]): Promise<MapMarkerData[]> {
  const stations = new Map<string, StationRecords>();

  for (const record of records) {
    if (record.displayable === false || !record.matched_station_id) continue;
    const group = stations.get(record.matched_station_id) ?? { government: [], community: [] };
    if (record.source.kind === "government") group.government.push(record);
    if (record.source.kind === "community") group.community.push(record);
    stations.set(record.matched_station_id, group);
  }

  const markers = await Promise.all(
    Array.from(stations.entries()).map(async ([stationId, group]) => {
      const government = newest(group.government);
      const community = newest(group.community);
      if (!government || !community) return null;

      const comparison = await compareRecords(government.id, community.id);
      const status = comparison.fields.length > 0 && comparison.fields.every((field) => field.status === "same_value_and_unit")
        ? "match" as const
        : "review" as const;

      return {
        id: `${government.id}:${community.id}`,
        name: community.matched_station_name ?? government.location.name ?? community.location.name ?? stationId,
        area: stationId,
        position: [government.location.latitude, government.location.longitude] as [number, number],
        status,
        compared: formatRelativeTime(Math.max(Date.parse(government.ingested_at), Date.parse(community.ingested_at))),
        matchedStationId: stationId,
        anchorSummary: summarizeAnchors(government, community),
        readings: comparison.fields.map(toMarkerReading),
      } satisfies MapMarkerData;
    }),
  );

  return markers.filter((marker): marker is MapMarkerData => marker !== null);
}

export function buildContributorSummaries(records: WaterQualityRecord[]): ContributorSummary[] {
  const contributors = new Map<string, WaterQualityRecord[]>();
  for (const record of records) {
    if (record.source.kind !== "community" || !record.signer_address) continue;
    const address = record.signer_address.toLowerCase();
    contributors.set(address, [...(contributors.get(address) ?? []), record]);
  }

  return Array.from(contributors.entries())
    .map(([address, contributions]) => {
      const locations = new Set(contributions.map((record) => record.matched_station_name ?? record.location.name).filter(Boolean));
      return {
        rank: 0,
        name: `Community issuer ${shortAddress(address)}`,
        handle: shortAddress(address),
        records: contributions.length,
        streak: activeWeekLabel(contributions),
        place: locations.size === 0 ? "Unmatched submissions" : `${locations.size} monitored ${locations.size === 1 ? "site" : "sites"}`,
        avatar: address.slice(2, 4).toUpperCase(),
      };
    })
    .sort((left, right) => right.records - left.records || left.handle.localeCompare(right.handle))
    .map((contributor, index) => ({ ...contributor, rank: index + 1 }));
}

function newest(records: WaterQualityRecord[]): WaterQualityRecord | undefined {
  return [...records].sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))[0];
}

function toMarkerReading(field: ComparisonField) {
  const canonicalField = field.field.replace(/ \[\d+\]$/, "");
  const parameter = WATER_QUALITY_PARAMETERS.find((item) => item.key === canonicalField);
  return {
    field: field.field,
    label: parameter?.label ?? canonicalField.replaceAll("_", " "),
    unit: field.government?.unit ?? field.community?.unit ?? parameter?.unit ?? "—",
    official: formatMeasurement(field.government?.value),
    community: formatMeasurement(field.community?.value),
    status: field.status,
  };
}

function formatMeasurement(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not reported";
  return String(value);
}

function summarizeAnchors(government: WaterQualityRecord, community: WaterQualityRecord): string {
  const statuses = [government.blockchain.status, community.blockchain.status];
  if (statuses.every((status) => status === "anchored")) return "Both records anchored";
  if (statuses.includes("anchored")) return "One record anchored";
  if (statuses.includes("simulated")) return "Simulated anchor";
  return "Not anchored";
}

function shortAddress(address: string): string {
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

function activeWeekLabel(records: WaterQualityRecord[]): string {
  const weeks = new Set(records.map((record) => {
    const date = new Date(record.ingested_at);
    const firstDay = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((date.getTime() - firstDay.getTime()) / 86_400_000 + firstDay.getUTCDay() + 1) / 7);
    return `${date.getUTCFullYear()}-${week}`;
  }));
  return `${weeks.size} active ${weeks.size === 1 ? "week" : "weeks"}`;
}

function formatRelativeTime(timestamp: number): string {
  if (!Number.isFinite(timestamp)) return "recently";
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} hr ago`;
  return `${Math.floor(seconds / 86_400)} d ago`;
}
