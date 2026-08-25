"use client";

import { useEffect, useMemo, useState } from "react";
import { compareRecords } from "../lib/api";
import type { ComparisonResponse, WaterQualityRecord } from "../lib/types";

export function ComparisonPanel({ records }: { records: WaterQualityRecord[] }) {
  const governmentRecords = useMemo(
    () => records.filter((record) => record.source.kind === "government"),
    [records],
  );
  const communityRecords = useMemo(
    () => records.filter((record) => record.source.kind === "community"),
    [records],
  );
  const [governmentId, setGovernmentId] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!governmentId && governmentRecords[0]) setGovernmentId(governmentRecords[0].id);
    if (!communityId && communityRecords[0]) setCommunityId(communityRecords[0].id);
  }, [communityId, communityRecords, governmentId, governmentRecords]);

  async function runComparison() {
    if (!governmentId || !communityId) return;
    setError(null);
    try {
      setComparison(await compareRecords(governmentId, communityId));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to compare records");
    }
  }

  return (
    <section className="comparison card">
      <div className="toolbar">
        <div>
          <h2>Compare source records</h2>
          <p>Differences and missing fields are shown without ranking either source.</p>
        </div>
        <button onClick={() => void runComparison()} disabled={!governmentId || !communityId}>
          Compare
        </button>
      </div>
      <div className="selectors">
        <label>
          Government record
          <select value={governmentId} onChange={(event) => setGovernmentId(event.target.value)}>
            <option value="">Select a record</option>
            {governmentRecords.map((record) => (
              <option key={record.id} value={record.id}>{record.source.provider} · {record.id.slice(0, 8)}</option>
            ))}
          </select>
        </label>
        <label>
          Community record
          <select value={communityId} onChange={(event) => setCommunityId(event.target.value)}>
            <option value="">Select a record</option>
            {communityRecords.map((record) => (
              <option key={record.id} value={record.id}>{record.source.provider} · {record.id.slice(0, 8)}</option>
            ))}
          </select>
        </label>
      </div>
      {error && <div className="notice">{error}</div>}
      {!governmentRecords.length || !communityRecords.length ? (
        <p className="empty">Ingest at least one government record and one community record to compare them.</p>
      ) : null}
      {comparison && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Field</th><th>Government</th><th>Community</th><th>Relationship</th></tr></thead>
            <tbody>
              {comparison.fields.map((field) => (
                <tr key={field.field}>
                  <th>{field.field}</th>
                  <td>{formatMeasurement(field.government)}</td>
                  <td>{formatMeasurement(field.community)}</td>
                  <td>{field.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {comparison.notes.map((note) => <p className="meta" key={note}>{note}</p>)}
        </div>
      )}
    </section>
  );
}

function formatMeasurement(measurement: ComparisonResponse["fields"][number]["government"]): string {
  if (!measurement) return "— missing";
  return `${String(measurement.value)}${measurement.unit ? ` ${measurement.unit}` : ""}`;
}
