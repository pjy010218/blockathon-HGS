"use client";

import { useState } from "react";
import { divIcon } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { verifyRecord } from "../lib/api";
import type { MapSite } from "../lib/types";
import {
  WATER_QUALITY_PARAMETERS,
  type WaterQualityParameterKey,
} from "../lib/water-quality-schema";
import "leaflet/dist/leaflet.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type MarkerStatus = "match" | "review" | "official";

function shortHash(hash?: string | null) {
  if (!hash) return "—";
  return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

function verifyHref(recordId?: string | null) {
  if (!recordId) return null;
  return `${API_URL}/api/v1/records/${recordId}/verify`;
}

function ChainStatus({
  transactionHash,
  transactionUrl,
  anchorStatus,
}: {
  transactionHash?: string | null;
  transactionUrl?: string | null;
  anchorStatus?: string | null;
}) {
  if (transactionUrl) {
    return (
      <a href={transactionUrl} target="_blank" rel="noreferrer" title={transactionHash ?? undefined}>
        View on explorer
      </a>
    );
  }
  if (anchorStatus === "simulated") {
    return <span title={transactionHash ?? undefined}>Simulated locally</span>;
  }
  return <span>Not anchored</span>;
}

function ProofLine({
  label,
  hash,
  transactionHash,
  transactionUrl,
  anchorStatus,
}: {
  label: string;
  hash?: string | null;
  transactionHash?: string | null;
  transactionUrl?: string | null;
  anchorStatus?: string | null;
}) {
  return (
    <div className="proof-line">
      <p className="proof-source">{label}</p>
      <dl>
        <div>
          <dt>Record hash</dt>
          <dd><code title={hash ?? undefined}>{shortHash(hash)}</code></dd>
        </div>
        <div>
          <dt>On-chain</dt>
          <dd>
            <ChainStatus
              transactionHash={transactionHash}
              transactionUrl={transactionUrl}
              anchorStatus={anchorStatus}
            />
          </dd>
        </div>
      </dl>
    </div>
  );
}

function SiteProof({ site }: { site: MapSite }) {
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "fail">("idle");
  const [detail, setDetail] = useState("");
  const officialOnly = site.kind === "official" || site.status === "official";

  async function check() {
    const ids = [site.community_record_id, site.government_record_id].filter(Boolean) as string[];
    if (!ids.length) return;
    setStatus("checking");
    try {
      const results = await Promise.all(ids.map((id) => verifyRecord(id)));
      const ok = results.every((item) => item.matches);
      setStatus(ok ? "ok" : "fail");
      setDetail(ok ? "Stored hashes still match." : "A stored hash no longer matches.");
    } catch {
      setStatus("fail");
      setDetail("The API could not verify these records.");
    }
  }

  const communityProof = verifyHref(site.community_record_id);
  const emsProof = verifyHref(site.government_record_id);

  return (
    <div className="popup-proof">
      {!officialOnly ? (
        <ProofLine
          label="Community"
          hash={site.community_hash}
          transactionHash={site.community_transaction_hash}
          transactionUrl={site.community_transaction_url}
          anchorStatus={site.community_anchor_status}
        />
      ) : null}
      <ProofLine
        label="EMS"
        hash={site.government_hash}
        transactionHash={site.government_transaction_hash}
        transactionUrl={site.government_transaction_url}
        anchorStatus={site.government_anchor_status}
      />
      <div className="proof-actions">
        <button type="button" onClick={() => void check()} disabled={status === "checking"}>
          {status === "checking" ? "Checking…" : "Check hashes"}
        </button>
        {communityProof ? <a href={communityProof} target="_blank" rel="noreferrer">Community JSON</a> : null}
        {emsProof ? <a href={emsProof} target="_blank" rel="noreferrer">EMS JSON</a> : null}
      </div>
      {status !== "idle" && status !== "checking" ? (
        <strong className={status === "ok" ? "proof-ok" : "proof-fail"}>{status === "ok" ? "Verified" : "Not verified"}</strong>
      ) : null}
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

function faceIcon(status: MarkerStatus) {
  const label = status === "match" ? "Matching readings" : status === "review" ? "Readings need review" : "Official EMS station";
  const mark = status === "match" ? "☺" : status === "review" ? "☹" : "●";
  const size = status === "official" ? 26 : 48;
  return divIcon({
    className: "water-marker-wrap",
    html: `<div class="water-marker ${status}" aria-label="${label}"><span>${mark}</span></div>`,
    iconSize: [size, status === "official" ? 26 : 57],
    iconAnchor: [size / 2, status === "official" ? 13 : 55],
    popupAnchor: [0, status === "official" ? -14 : -48],
  });
}

export default function WaterMap({
  filter,
  sites,
}: {
  filter: "all" | MarkerStatus;
  sites: MapSite[];
}) {
  const visible = sites.filter((site) => site.displayable && (filter === "all" || site.status === filter));
  const official = visible.filter((site) => site.status === "official");
  const pairs = visible.filter((site) => site.status !== "official");

  return (
    <MapContainer center={[49.25, -123.05]} zoom={10} minZoom={7} scrollWheelZoom className="leaflet-map" zoomControl>
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {official.map((marker) => (
        <Marker key={marker.id} position={marker.position as [number, number]} icon={faceIcon("official")} zIndexOffset={0}>
          <Popup minWidth={320} maxWidth={380} autoPanPadding={[24, 72]}>
            <OfficialPopup marker={marker} />
          </Popup>
        </Marker>
      ))}
      {pairs.map((marker) => (
        <Marker key={marker.id} position={marker.position as [number, number]} icon={faceIcon(marker.status)} zIndexOffset={400}>
          <Popup minWidth={350} maxWidth={390} autoPanPadding={[24, 72]}>
            <PairPopup marker={marker} />
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

function PairPopup({ marker }: { marker: MapSite }) {
  return (
    <div className="marker-popup">
      <div className="popup-top">
        <span className={`popup-face ${marker.status}`}>{marker.status === "match" ? "☺" : "☹"}</span>
        <div><small>{marker.area}</small><h3>{marker.name}</h3></div>
      </div>
      <div className={`popup-status ${marker.status}`}><i /> {marker.status === "match" ? "Datasets match" : "Difference needs review"}</div>
      <SiteProof site={marker} />
      <div className="popup-table">
        <span>Parameter</span><span>EMS</span><span>Community</span>
        {marker.readings.map((reading) => {
          const parameter = WATER_QUALITY_PARAMETERS.find((item) => item.key === reading.parameter as WaterQualityParameterKey);
          return (
            <div className="popup-row" key={reading.parameter}>
              <b>{parameter?.label ?? reading.parameter}<small>{parameter?.unit}</small></b>
              <span>{reading.official}</span>
              <span>{reading.community}</span>
            </div>
          );
        })}
      </div>
      <p>{marker.matched_station_id} · E. coli may be reported as MPN/100mL by EMS · {marker.compared}</p>
    </div>
  );
}

function OfficialPopup({ marker }: { marker: MapSite }) {
  return (
    <div className="marker-popup">
      <div className="popup-top">
        <span className="popup-face official">EMS</span>
        <div><small>{marker.area}</small><h3>{marker.name}</h3></div>
      </div>
      <div className="popup-status official"><i /> Official EMS station · no community pair within 50 m</div>
      <SiteProof site={marker} />
      {marker.readings.length ? (
        <div className="popup-table official-table">
          <span>Parameter</span><span>EMS</span>
          {marker.readings.map((reading) => {
            const parameter = WATER_QUALITY_PARAMETERS.find((item) => item.key === reading.parameter as WaterQualityParameterKey);
            return (
              <div className="popup-row official-row" key={reading.parameter}>
                <b>{parameter?.label ?? reading.parameter}<small>{parameter?.unit}</small></b>
                <span>{reading.official}</span>
              </div>
            );
          })}
        </div>
      ) : null}
      <p>{marker.matched_station_id}{marker.compared ? ` · ${marker.compared}` : ""}</p>
    </div>
  );
}
