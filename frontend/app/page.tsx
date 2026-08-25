"use client";

import { useEffect, useState } from "react";
import { RecordCard } from "../components/RecordCard";
import { ComparisonPanel } from "../components/ComparisonPanel";
import { listRecords } from "../lib/api";
import type { WaterQualityRecord } from "../lib/types";

export default function Home() {
  const [records, setRecords] = useState<WaterQualityRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setRecords(await listRecords());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load records");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  return (
    <main>
      <p className="eyebrow">SDG 14 · Life Below Water</p>
      <h1>See the record. Check the history.</h1>
      <p className="intro">
        A community-auditable view of water-quality measurements. Source records remain
        identifiable, differences remain visible, and hashes make later changes detectable.
      </p>
      <div className="principle">
        This application does not rank sources or say which data is more trustworthy. It
        displays provenance and differences so readers can make their own assessment.
      </div>

      <section>
        <div className="toolbar">
          <div>
            <h2>Published records</h2>
            <p>{records.length} record{records.length === 1 ? "" : "s"} in the current API</p>
          </div>
          <button onClick={() => void refresh()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh records"}
          </button>
        </div>
        {error && <div className="notice">{error}. Start the FastAPI service on port 8000.</div>}
        {!loading && !error && records.length === 0 && (
          <p className="empty">No records have been ingested yet. Connect a source adapter or submit a record through the API.</p>
        )}
        <div className="grid">{records.map((record) => <RecordCard key={record.id} record={record} />)}</div>
      </section>
      <ComparisonPanel records={records} />
    </main>
  );
}
