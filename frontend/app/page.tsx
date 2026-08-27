"use client";

import dynamic from "next/dynamic";
import { FormEvent, useMemo, useState } from "react";
import { WATER_QUALITY_PARAMETERS } from "../lib/water-quality-schema";

const WaterMap = dynamic(() => import("../components/WaterMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Charting the Salish Sea…</div>,
});

type Tab = "map" | "data" | "leaderboard";
type CertificateState = "none" | "pending" | "granted";

const leaders = [
  { rank: 1, name: "Salish Seakeepers", handle: "0x8F2A…91C4", records: 184, streak: "28 weeks", place: "Vancouver Island", avatar: "SS" },
  { rank: 2, name: "Fraser Watch", handle: "0x31BD…7A09", records: 157, streak: "19 weeks", place: "Lower Mainland", avatar: "FW" },
  { rank: 3, name: "North Shore Streamkeepers", handle: "0x7C11…44BE", records: 132, streak: "16 weeks", place: "North Vancouver", avatar: "NS" },
  { rank: 4, name: "Raincoast Field Lab", handle: "0x02DA…5F81", records: 98, streak: "14 weeks", place: "Central Coast", avatar: "RF" },
  { rank: 5, name: "Kitsilano Citizen Science", handle: "0xA6E8…113D", records: 76, streak: "11 weeks", place: "Vancouver", avatar: "KC" },
];

function Icon({ name }: { name: "map" | "drop" | "trophy" | "wallet" | "arrow" | "shield" | "check" }) {
  const paths = {
    map: <><path d="m3 6 5-2 8 3 5-2v13l-5 2-8-3-5 2Z"/><path d="M8 4v13M16 7v13"/></>,
    drop: <path d="M12 2S5.5 9.1 5.5 14.3a6.5 6.5 0 0 0 13 0C18.5 9.1 12 2 12 2Z"/>,
    trophy: <><path d="M8 4h8v5a4 4 0 0 1-8 0Z"/><path d="M12 13v4m-4 3h8M8 6H4v2a4 4 0 0 0 4 4m8-6h4v2a4 4 0 0 1-4 4"/></>,
    wallet: <><path d="M4 6h15a2 2 0 0 1 2 2v10H4a2 2 0 0 1-2-2V6a3 3 0 0 1 3-3h12v3"/><path d="M16 11h5v4h-5a2 2 0 0 1 0-4Z"/></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
    shield: <><path d="M12 3 5 6v5c0 4.5 2.8 7.8 7 10 4.2-2.2 7-5.5 7-10V6Z"/><path d="m9 12 2 2 4-4"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="icon">{paths[name]}</svg>;
}

export default function Home() {
  const [tab, setTab] = useState<Tab>("map");
  const [wallet, setWallet] = useState<string | null>(null);
  const [walletBusy, setWalletBusy] = useState(false);
  const [certificate, setCertificate] = useState<CertificateState>("none");
  const [submitted, setSubmitted] = useState(false);
  const shortWallet = useMemo(() => wallet ? `${wallet.slice(0, 6)}…${wallet.slice(-4)}` : null, [wallet]);

  async function connectWallet() {
    setWalletBusy(true);
    try {
      const { MetaMaskSDK } = await import("@metamask/sdk");
      const sdk = new MetaMaskSDK({ dappMetadata: { name: "Tideproof", url: window.location.href } });
      const accounts = await sdk.connect();
      if (accounts?.[0]) setWallet(accounts[0]);
    } catch (error) {
      console.error("MetaMask connection was not completed", error);
    } finally { setWalletBusy(false); }
  }

  function requestCertificate() {
    setCertificate("pending");
    // BACKEND INTEGRATION: replace this preview timer with the certificate application
    // endpoint and update state from the returned application/certificate status.
    window.setTimeout(() => setCertificate("granted"), 1100);
  }

  function submitReading(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    // BACKEND INTEGRATION: send the validated form payload to the ingestion endpoint.
    // The backend owns storage, canonical hashing, and blockchain anchoring.
  }

  const tabs: { id: Tab; label: string; icon: "map" | "drop" | "trophy" }[] = [
    { id: "map", label: "Map", icon: "map" }, { id: "data", label: "Data", icon: "drop" }, { id: "leaderboard", label: "Leaderboard", icon: "trophy" },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setTab("map")} aria-label="Tideproof home"><span className="brand-mark"><span /></span><span>Tideproof</span><small>BC water record</small></button>
        <nav className="tabs" aria-label="Primary navigation">{tabs.map((item) => <button key={item.id} className={tab === item.id ? "tab active" : "tab"} onClick={() => setTab(item.id)} aria-current={tab === item.id ? "page" : undefined}><Icon name={item.icon} /> {item.label}</button>)}</nav>
        <button className="wallet-button" onClick={connectWallet} disabled={walletBusy}><Icon name="wallet" /><span>{walletBusy ? "Connecting…" : shortWallet ?? "Connect wallet"}</span>{wallet && <i className="online-dot" />}</button>
      </header>
      <main className="main-stage">
        {tab === "map" && <MapView onOpenData={() => setTab("data")} />}
        {tab === "data" && <DataView certificate={certificate} wallet={shortWallet} submitted={submitted} onConnect={connectWallet} onRequest={requestCertificate} onSubmit={submitReading} />}
        {tab === "leaderboard" && <LeaderboardView />}
      </main>
    </div>
  );
}

function MapView({ onOpenData }: { onOpenData: () => void }) {
  const [filter, setFilter] = useState<"all" | "match" | "review">("all");
  return <section className="map-view view-enter" aria-labelledby="map-title">
    <div className="map-heading"><div><p className="kicker"><span className="live-pulse" /> Live comparison map</p><h1 id="map-title">Where the water<br />records <em>agree.</em></h1></div><p className="map-intro">Community and official readings, compared site by site across British Columbia.</p></div>
    <div className="map-frame"><WaterMap filter={filter} /><div className="map-tools" aria-label="Filter map markers"><button className={filter === "all" ? "selected" : ""} onClick={() => setFilter("all")}>All sites <b>8</b></button><button className={filter === "match" ? "selected" : ""} onClick={() => setFilter("match")}><span className="legend-face happy">☺</span> Match <b>5</b></button><button className={filter === "review" ? "selected" : ""} onClick={() => setFilter("review")}><span className="legend-face sad">☹</span> Needs review <b>3</b></button></div><div className="map-note"><Icon name="shield" /><span><b>Records, not verdicts.</b> Markers show whether two datasets meet a backend-defined match threshold.</span></div></div>
    <div className="map-footer"><p><strong>Last comparison</strong> Today, 09:42 PT · Prototype records</p><button className="text-button" onClick={onOpenData}>Contribute a reading <Icon name="arrow" /></button></div>
  </section>;
}

type DataViewProps = { certificate: CertificateState; wallet: string | null; submitted: boolean; onConnect: () => void; onRequest: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void };

function DataView({ certificate, wallet, submitted, onConnect, onRequest, onSubmit }: DataViewProps) {
  return <section className="content-view view-enter" aria-labelledby="data-title">
    <header className="page-heading"><p className="kicker">Community data</p><h1 id="data-title">Add a reading.<br /><em>Keep it accountable.</em></h1><p>Certified contributors can submit field measurements. Every accepted record will be preserved, hashed, and anchored by the backend.</p></header>
    <div className="data-layout">
      <aside className={`certificate-card certificate-${certificate}`}><div className="certificate-top"><span className="seal"><Icon name={certificate === "granted" ? "check" : "shield"} /></span><span className="status-pill">{certificate === "granted" ? "Certificate active" : certificate === "pending" ? "Reviewing" : "Required first"}</span></div><h2>Contributor certificate</h2><p>Connect a wallet and verify who stands behind each measurement.</p><dl><div><dt>Wallet</dt><dd>{wallet ?? "Not connected"}</dd></div><div><dt>Status</dt><dd>{certificate === "granted" ? "Granted · prototype" : certificate === "pending" ? "Application pending" : "Not applied"}</dd></div></dl>{!wallet && <button className="primary-button dark" onClick={onConnect}><Icon name="wallet" /> Connect wallet</button>}{wallet && certificate === "none" && <button className="primary-button dark" onClick={onRequest}>Apply for certificate <Icon name="arrow" /></button>}{certificate === "pending" && <div className="reviewing"><span /> Checking application…</div>}{certificate === "granted" && <div className="granted-note"><Icon name="check" /> Ready to contribute</div>}<small>Prototype flow only. Identity review and certificate issuance belong to the backend.</small></aside>
      <div className={certificate === "granted" ? "form-card" : "form-card locked"}><div className="form-header"><div><p className="step-label">Water quality record</p><h2>Field measurement</h2></div><span>{certificate === "granted" ? "Certificate verified" : "Locked"}</span></div><form onSubmit={onSubmit}><fieldset disabled={certificate !== "granted"}><div className="form-grid"><label className="wide">Site name<input required name="site" placeholder="e.g. False Creek East Basin" /></label><label>Sampled on<input required name="sampledAt" type="datetime-local" /></label><label>Collection method<select name="method" defaultValue="grab"><option value="grab">Grab sample</option><option value="sensor">In-situ sensor</option><option value="lab">Lab analysis</option></select></label><label>Latitude<input required name="latitude" inputMode="decimal" placeholder="49.2827" /></label><label>Longitude<input required name="longitude" inputMode="decimal" placeholder="−123.1207" /></label></div><div className="measurements-title"><h3>Comparable measurements</h3><span>Community ↔ EMS intersection · leave untested values blank</span></div><div className="metric-grid">{WATER_QUALITY_PARAMETERS.map((parameter) => <label key={parameter.key}><span>{parameter.label}</span><div><input name={parameter.key} inputMode="decimal" placeholder={parameter.placeholder} aria-describedby={parameter.unitNote ? `${parameter.key}-note` : undefined} /><i>{parameter.unit}</i></div>{parameter.unitNote && <small id={`${parameter.key}-note`}>{parameter.unitNote}</small>}</label>)}</div><label className="notes-label">Field notes<textarea name="notes" rows={3} placeholder="Weather, tide, equipment, or anything that helps interpret this sample." /></label><div className="submit-row"><p><Icon name="shield" /> The backend will hash the exact accepted payload.</p><button className="primary-button" type="submit">Submit reading <Icon name="arrow" /></button></div></fieldset></form>{certificate !== "granted" && <div className="lock-overlay"><span><Icon name="shield" /></span><b>Certificate needed</b><p>Complete the contributor step to unlock this form.</p></div>}{submitted && <div className="success-banner"><Icon name="check" /><div><b>Reading ready for handoff</b><span>Frontend validation passed. No data was uploaded in this prototype.</span></div></div>}</div>
    </div>
  </section>;
}

function LeaderboardView() {
  return <section className="content-view leaderboard-view view-enter" aria-labelledby="leaderboard-title">
    <header className="page-heading leaderboard-heading"><div><p className="kicker">Community ledger · All time</p><h1 id="leaderboard-title">Proof of showing up.</h1></div><p>Reliable records come from people who return. This board recognizes sustained, verified fieldwork—not popularity.</p></header>
    <div className="podium">{leaders.slice(0, 3).map((leader) => <article className={`podium-card place-${leader.rank}`} key={leader.rank}><span className="rank-badge">{leader.rank}</span><div className="avatar">{leader.avatar}</div><div><h2>{leader.name}</h2><p>{leader.place}</p></div><strong>{leader.records}<small>verified records</small></strong></article>)}</div>
    <div className="leader-table-wrap"><div className="leader-table-title"><div><h2>Trusted contributors</h2><p>Ranked by accepted, certificate-backed records</p></div><span>Updated today</span></div><div className="leader-table" role="table" aria-label="Contributor leaderboard"><div className="leader-row leader-labels" role="row"><span>Rank</span><span>Contributor</span><span>Wallet</span><span>Current streak</span><span>Records</span></div>{leaders.map((leader) => <div className="leader-row" role="row" key={leader.rank}><span className="table-rank">{String(leader.rank).padStart(2, "0")}</span><span className="contributor"><i>{leader.avatar}</i><span><b>{leader.name}</b><small>{leader.place}</small></span></span><span className="mono">{leader.handle}</span><span>{leader.streak}</span><strong>{leader.records}</strong></div>)}</div></div>
    <p className="leader-note"><Icon name="shield" /> Rankings will be calculated from backend-verified contributions. Placeholder data is shown for interface development.</p>
  </section>;
}
