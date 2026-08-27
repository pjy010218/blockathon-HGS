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

type MarkerStatus = "match" | "review";

function shortHash(hash?: string | null) {
  if (!hash) return "—";
  return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

function SiteProof({ site }: { site: MapSite }) {
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "fail">("idle");
  const [detail, setDetail] = useState("");

  async function check() {
    if (!site.community_record_id || !site.government_record_id) return;
    setStatus("checking");
    try {
      const [community, government] = await Promise.all([
        verifyRecord(site.community_record_id),
        verifyRecord(site.government_record_id),
      ]);
      const ok = community.matches && government.matches;
      setStatus(ok ? "ok" : "fail");
      setDetail(ok ? "Stored hashes still match both records." : "A stored hash no longer matches.");
    } catch {
      setStatus("fail");
      setDetail("The API could not verify these records.");
    }
  }

  return (
    <div className="popup-proof">
      <p>Community {shortHash(site.community_hash)}</p>
      <p>EMS {shortHash(site.government_hash)}</p>
      <button type="button" onClick={() => void check()} disabled={status === "checking"}>
        {status === "checking" ? "Checking…" : "Check proof"}
      </button>
      {status !== "idle" && status !== "checking" ? (
        <strong className={status === "ok" ? "proof-ok" : "proof-fail"}>{status === "ok" ? "Verified" : "Not verified"}</strong>
      ) : null}
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

function faceIcon(status: MarkerStatus) {
  return divIcon({
    className: "water-marker-wrap",
    html: `<div class="water-marker ${status}" aria-label="${status === "match" ? "Matching readings" : "Readings need review"}"><span>${status === "match" ? "☺" : "☹"}</span></div>`,
    iconSize: [48, 57],
    iconAnchor: [24, 55],
    popupAnchor: [0, -48],
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

  return (
    <MapContainer center={[49.274, -123.105]} zoom={11} minZoom={7} scrollWheelZoom className="leaflet-map" zoomControl>
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {visible.map((marker) => (
        <Marker key={marker.id} position={marker.position as [number, number]} icon={faceIcon(marker.status)}>
          <Popup minWidth={350} maxWidth={390}>
            <div className="marker-popup">
              <div className="popup-top">
                <span className={`popup-face ${marker.status}`}>{marker.status === "match" ? "☺" : "☹"}</span>
                <div><small>{marker.area}</small><h3>{marker.name}</h3></div>
              </div>
              <div className={`popup-status ${marker.status}`}><i /> {marker.status === "match" ? "Datasets match" : "Difference needs review"}</div>
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
              <SiteProof site={marker} />
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
