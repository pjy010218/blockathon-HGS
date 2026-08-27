"use client";

import { divIcon } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import {
  WATER_QUALITY_PARAMETERS,
  type WaterQualityParameterKey,
} from "../lib/water-quality-schema";
import "leaflet/dist/leaflet.css";

type MarkerStatus = "match" | "review";
type MarkerReading = {
  parameter: WaterQualityParameterKey;
  official: string;
  community: string;
};
type WaterMarker = {
  id: number;
  name: string;
  area: string;
  position: [number, number];
  status: MarkerStatus;
  compared: string;
  readings: MarkerReading[];
};

const sampleValues = [7.8, 9.1, 325, 14.2, 0.18, 0.01, 118, 12];
const samplePrecision = [1, 1, 0, 1, 2, 2, 0, 0];

function placeholderReadings(offset: number, status: MarkerStatus): MarkerReading[] {
  return WATER_QUALITY_PARAMETERS.map((parameter, index) => {
    const officialValue = sampleValues[index] + offset * [0.03, 0.08, 6, 0.25, 0.01, 0.002, 2, 1][index];
    const difference = status === "review" && [1, 4, 7].includes(index)
      ? [0, -1.7, 0, 0, 0.16, 0, 0, 21][index]
      : [0.02, 0.1, -3, 0.1, -0.01, 0, 1, -1][index];
    const precision = samplePrecision[index];

    return {
      parameter: parameter.key,
      official: officialValue.toFixed(precision),
      community: (officialValue + difference).toFixed(precision),
    };
  });
}

// BACKEND INTEGRATION: replace these markers with canonical comparison records.
// The backend determines marker status and normalizes both upstream datasets to
// WATER_QUALITY_PARAMETERS before returning measurement values.
const markerSites = [
  { id: 1, name: "False Creek", area: "East Basin", position: [49.2743, -123.1057] as [number, number], status: "match" as const, compared: "2 hours ago" },
  { id: 2, name: "English Bay", area: "Kitsilano Point", position: [49.2817, -123.1512] as [number, number], status: "match" as const, compared: "5 hours ago" },
  { id: 3, name: "Burrard Inlet", area: "Second Narrows", position: [49.3024, -123.0268] as [number, number], status: "review" as const, compared: "Yesterday" },
  { id: 4, name: "Iona Beach", area: "North Arm", position: [49.2162, -123.2141] as [number, number], status: "review" as const, compared: "Yesterday" },
  { id: 5, name: "Deep Cove", area: "Indian Arm", position: [49.3268, -122.9486] as [number, number], status: "match" as const, compared: "3 days ago" },
  { id: 6, name: "Steveston Harbour", area: "Fraser River", position: [49.1241, -123.1832] as [number, number], status: "review" as const, compared: "3 days ago" },
  { id: 7, name: "Ambleside", area: "West Vancouver", position: [49.3247, -123.1475] as [number, number], status: "match" as const, compared: "4 days ago" },
  { id: 8, name: "Burnaby Lake", area: "Still Creek", position: [49.2425, -122.9361] as [number, number], status: "match" as const, compared: "5 days ago" },
];

const markers: WaterMarker[] = markerSites.map((site, index) => ({
  ...site,
  readings: placeholderReadings(index - 3, site.status),
}));

function faceIcon(status: MarkerStatus) {
  return divIcon({
    className: "water-marker-wrap",
    html: `<div class="water-marker ${status}" aria-label="${status === "match" ? "Matching readings" : "Readings need review"}"><span>${status === "match" ? "☺" : "☹"}</span></div>`,
    iconSize: [48, 57],
    iconAnchor: [24, 55],
    popupAnchor: [0, -48],
  });
}

export default function WaterMap({ filter }: { filter: "all" | MarkerStatus }) {
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
                {marker.readings.map((reading) => {
                  const parameter = WATER_QUALITY_PARAMETERS.find((item) => item.key === reading.parameter)!;
                  return (
                    <div className="popup-row" key={reading.parameter}>
                      <b>{parameter.label}<small>{parameter.unit}</small></b>
                      <span>{reading.official}</span>
                      <span>{reading.community}</span>
                    </div>
                  );
                })}
              </div>
              <p>E. coli may be reported as MPN/100mL by EMS · Compared {marker.compared}</p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
