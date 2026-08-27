"use client";

import { divIcon } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

type MarkerStatus = "match" | "review";
type WaterMarker = { id: number; name: string; area: string; position: [number, number]; status: MarkerStatus; compared: string; readings: { label: string; official: string; community: string }[] };

// BACKEND INTEGRATION: replace these markers with a mapped response from the
// comparison endpoint once match thresholds and database queries are available.
const markers: WaterMarker[] = [
  { id: 1, name: "False Creek", area: "East Basin", position: [49.2743, -123.1057], status: "match", compared: "2 hours ago", readings: [{ label: "pH", official: "7.8", community: "7.8" }, { label: "Temp.", official: "16.2°C", community: "16.3°C" }] },
  { id: 2, name: "English Bay", area: "Kitsilano Point", position: [49.2817, -123.1512], status: "match", compared: "5 hours ago", readings: [{ label: "pH", official: "8.1", community: "8.0" }, { label: "DO", official: "9.3", community: "9.2" }] },
  { id: 3, name: "Burrard Inlet", area: "Second Narrows", position: [49.3024, -123.0268], status: "review", compared: "Yesterday", readings: [{ label: "Turbidity", official: "1.6 NTU", community: "3.9 NTU" }, { label: "pH", official: "7.9", community: "7.5" }] },
  { id: 4, name: "Iona Beach", area: "North Arm", position: [49.2162, -123.2141], status: "review", compared: "Yesterday", readings: [{ label: "DO", official: "8.8", community: "7.1" }, { label: "Temp.", official: "15.4°C", community: "15.6°C" }] },
  { id: 5, name: "Deep Cove", area: "Indian Arm", position: [49.3268, -122.9486], status: "match", compared: "3 days ago", readings: [{ label: "pH", official: "8.0", community: "8.0" }, { label: "Temp.", official: "13.1°C", community: "13.0°C" }] },
  { id: 6, name: "Steveston Harbour", area: "Fraser River", position: [49.1241, -123.1832], status: "review", compared: "3 days ago", readings: [{ label: "Turbidity", official: "7.2 NTU", community: "11.1 NTU" }, { label: "pH", official: "7.4", community: "7.3" }] },
  { id: 7, name: "Ambleside", area: "West Vancouver", position: [49.3247, -123.1475], status: "match", compared: "4 days ago", readings: [{ label: "pH", official: "8.1", community: "8.1" }, { label: "DO", official: "9.5", community: "9.4" }] },
  { id: 8, name: "Burnaby Lake", area: "Still Creek", position: [49.2425, -122.9361], status: "match", compared: "5 days ago", readings: [{ label: "pH", official: "7.2", community: "7.3" }, { label: "Temp.", official: "18.2°C", community: "18.1°C" }] },
];

function faceIcon(status: MarkerStatus) {
  return divIcon({ className: "water-marker-wrap", html: `<div class="water-marker ${status}" aria-label="${status === "match" ? "Matching readings" : "Readings need review"}"><span>${status === "match" ? "☺" : "☹"}</span></div>`, iconSize: [48, 57], iconAnchor: [24, 55], popupAnchor: [0, -48] });
}

export default function WaterMap({ filter }: { filter: "all" | MarkerStatus }) {
  const visible = markers.filter((marker) => filter === "all" || marker.status === filter);
  return <MapContainer center={[49.274, -123.105]} zoom={11} minZoom={7} scrollWheelZoom className="leaflet-map" zoomControl>
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {visible.map((marker) => <Marker key={marker.id} position={marker.position} icon={faceIcon(marker.status)}><Popup minWidth={260}><div className="marker-popup"><div className="popup-top"><span className={`popup-face ${marker.status}`}>{marker.status === "match" ? "☺" : "☹"}</span><div><small>{marker.area}</small><h3>{marker.name}</h3></div></div><div className="popup-status"><i /> {marker.status === "match" ? "Datasets match" : "Difference needs review"}</div><div className="popup-table"><span>Measure</span><span>Official</span><span>Community</span>{marker.readings.map((reading) => <div className="popup-row" key={reading.label}><b>{reading.label}</b><span>{reading.official}</span><span>{reading.community}</span></div>)}</div><p>Compared {marker.compared}</p></div></Popup></Marker>)}
  </MapContainer>;
}
