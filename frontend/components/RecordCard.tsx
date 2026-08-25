import type { WaterQualityRecord } from "../lib/types";

export function RecordCard({ record }: { record: WaterQualityRecord }) {
  return (
    <article className="card">
      <p className="eyebrow">{record.source.kind} source</p>
      <h3>{record.source.provider}</h3>
      <p className="meta">
        {record.location.name ?? "Unnamed location"} · {new Date(record.observed_at).toLocaleString()}
      </p>
      <p>
        {record.measurements.length} measurement{record.measurements.length === 1 ? "" : "s"}
      </p>
      <div className="hash">SHA-256: {record.content_hash}</div>
      <p className="meta">Blockchain status: {record.blockchain.status}</p>
    </article>
  );
}
