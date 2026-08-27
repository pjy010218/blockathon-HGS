"use client";

import { divIcon } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export type MarkerStatus = "match" | "review";
export type MapMarkerReading = {
  field: string;
  label: string;
  unit: string;
  official: string;
  community: string;
  status: string;
};
export type MapMarkerData = {
  id: string;
  name: string;
  area: string;
  position: [number, number];
  status: MarkerStatus;
  compared: string;
  matchedStationId: string;
  anchorSummary: string;
  readings: MapMarkerReading[];
};

function faceIcon(status: MarkerStatus) {
  return divIcon({
    className: "water-marker-wrap",
    html: `<div class="water-marker ${status}" aria-label="${status === "match" ? "Matching readings" : "Readings need review"}"><span>${status === "match" ? "☺" : "☹"}</span></div>`,
    iconSize: [48, 57],
    iconAnchor: [24, 55],
    popupAnchor: [0, -48],
  });
}

export default function WaterMap({ markers, filter }: { markers: MapMarkerData[]; filter: "all" | MarkerStatus }) {
  const visible = markers.filter((marker) => filter === "all" || marker.status === filter);

  return (
    <MapContainer center={[49.274, -123.105]} zoom={11} minZoom={7} scrollWheelZoom className="leaflet-map" zoomControl>
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {visible.map((marker) => (
        <Marker key={marker.id} position={marker.position} icon={faceIcon(marker.status)}>
          <Popup minWidth={350} maxWidth={390}>
            <div className="marker-popup">
              <div className="popup-top">
                <span className={`popup-face ${marker.status}`}>{marker.status === "match" ? "☺" : "☹"}</span>
                <div><small>{marker.area}</small><h3>{marker.name}</h3></div>
              </div>
              <div className={`popup-status ${marker.status}`}><i /> {marker.status === "match" ? "Datasets match" : "Difference needs review"}</div>
              <div className="popup-table">
                <span>Parameter</span><span>EMS</span><span>Community</span>
                {marker.readings.map((reading) => (
                  <div className={`popup-row ${reading.status}`} key={reading.field}>
                    <b>{reading.label}<small>{reading.unit}</small></b>
                    <span>{reading.official}</span>
                    <span>{reading.community}</span>
                  </div>
                ))}
              </div>
              <p>{marker.matchedStationId} · {marker.anchorSummary} · Compared {marker.compared}</p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
