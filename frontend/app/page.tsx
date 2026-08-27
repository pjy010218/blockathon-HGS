"use client";

import dynamic from "next/dynamic";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError, listMapSites, listStations, submitCommunityRecord } from "../lib/api";
import {
  buildCommunityRecord,
  signCommunityRecord,
  type WalletProvider,
} from "../lib/community-submission";
import type { GovernmentStation, MapSite } from "../lib/types";
import { WATER_QUALITY_PARAMETERS } from "../lib/water-quality-schema";

const WaterMap = dynamic(() => import("../components/WaterMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Charting the Salish Sea…</div>,
});

type Tab = "map" | "data" | "leaderboard";
type SubmissionState = {
  phase: "idle" | "preparing" | "signing" | "submitting" | "submitted" | "unmatched" | "error";
  message?: string;
  contentHash?: string;
};

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
  const [walletProvider, setWalletProvider] = useState<WalletProvider | null>(null);
  const [walletBusy, setWalletBusy] = useState(false);
  const [walletError, setWalletError] = useState<string | null>(null);
  const [submission, setSubmission] = useState<SubmissionState>({ phase: "idle" });
  const shortWallet = useMemo(() => wallet ? `${wallet.slice(0, 6)}…${wallet.slice(-4)}` : null, [wallet]);

  async function connectWallet() {
    setWalletBusy(true);
    setWalletError(null);
    try {
      const { MetaMaskSDK } = await import("@metamask/sdk");
      const sdk = new MetaMaskSDK({ dappMetadata: { name: "Tideproof", url: window.location.href } });
      const accounts = await sdk.connect();
      const provider = sdk.getProvider();
      if (!accounts?.[0] || !provider) throw new Error("MetaMask did not provide an account.");
      setWallet(accounts[0]);
      setWalletProvider(provider as WalletProvider);
    } catch (error) {
      setWalletError(error instanceof Error ? error.message : "MetaMask connection was not completed.");
    } finally { setWalletBusy(false); }
  }

  async function submitReading(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!wallet || !walletProvider) {
      setSubmission({ phase: "error", message: "Connect MetaMask before signing this record." });
      return;
    }

    try {
      setSubmission({ phase: "preparing", message: "Validating canonical measurements…" });
      const form = event.currentTarget;
      const record = buildCommunityRecord(new FormData(form));
      const anchor = new FormData(form).get("anchor") === "on";
      setSubmission({ phase: "signing", message: "Confirm the content-hash signature in MetaMask." });
      const payload = await signCommunityRecord(record, wallet, walletProvider, anchor);
      setSubmission({ phase: "submitting", message: "Sending the signed record to the ingest API…", contentHash: payload.signedContentHash });
      const created = await submitCommunityRecord(payload);

      if (created.displayable === false) {
        setSubmission({ phase: "unmatched", message: "Record accepted, but no government station was found within 50 m. It will not appear on the default map.", contentHash: created.content_hash });
      } else {
        setSubmission({ phase: "submitted", message: "Signed record accepted by the ingest API.", contentHash: created.content_hash });
        form.reset();
      }
    } catch (error) {
      const message = error instanceof ApiError || error instanceof Error
        ? error.message
        : "The signed record could not be submitted.";
      setSubmission({ phase: "error", message });
    }
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
        {tab === "data" && <DataView wallet={shortWallet} walletError={walletError} submission={submission} onConnect={connectWallet} onSubmit={submitReading} />}
        {tab === "leaderboard" && <LeaderboardView />}
      </main>
    </div>
  );
}

function MapView({ onOpenData }: { onOpenData: () => void }) {
  const [filter, setFilter] = useState<"all" | "match" | "review">("all");
  const [sites, setSites] = useState<MapSite[]>([]);
  const [mapNote, setMapNote] = useState("Loading comparisons…");

  useEffect(() => {
    let active = true;
    void listMapSites()
      .then((items) => {
        if (!active) return;
        setSites(items);
        setMapNote(items.length ? "Imported pairs with stored proofs · records, not verdicts." : "No matched pairs yet. Start the API with DEMO_SEED=1 and DATABASE_URL.");
      })
      .catch(() => {
        if (!active) return;
        setSites([]);
        setMapNote("API map comparisons are not available yet.");
      });
    return () => { active = false; };
  }, []);

  const matchCount = sites.filter((site) => site.status === "match").length;
  const reviewCount = sites.filter((site) => site.status === "review").length;

  return <section className="map-view view-enter" aria-labelledby="map-title">
    <div className="map-heading"><div><p className="kicker"><span className="live-pulse" /> Live comparison map</p><h1 id="map-title">Where the water<br />records <em>agree.</em></h1></div><p className="map-intro">Community and official readings, compared site by site across British Columbia.</p></div>
    <div className="map-frame"><WaterMap filter={filter} sites={sites} /><div className="map-tools" aria-label="Filter map markers"><button className={filter === "all" ? "selected" : ""} onClick={() => setFilter("all")}>All sites <b>{sites.length}</b></button><button className={filter === "match" ? "selected" : ""} onClick={() => setFilter("match")}><span className="legend-face happy">☺</span> Match <b>{matchCount}</b></button><button className={filter === "review" ? "selected" : ""} onClick={() => setFilter("review")}><span className="legend-face sad">☹</span> Needs review <b>{reviewCount}</b></button></div><div className="map-note"><Icon name="shield" /><span><b>Records, not verdicts.</b> {mapNote}</span></div></div>
    <div className="map-footer"><p><strong>Last comparison</strong> {sites[0]?.compared ?? "Waiting for API data"}</p><button className="text-button" onClick={onOpenData}>Contribute a reading <Icon name="arrow" /></button></div>
  </section>;
}

type DataViewProps = { wallet: string | null; walletError: string | null; submission: SubmissionState; onConnect: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void> };

function DataView({ wallet, walletError, submission, onConnect, onSubmit }: DataViewProps) {
  const [stations, setStations] = useState<GovernmentStation[]>([]);
  const [stationDirectoryReady, setStationDirectoryReady] = useState(false);
  const isSubmitting = ["preparing", "signing", "submitting"].includes(submission.phase);

  useEffect(() => {
    let active = true;
    void listStations()
      .then((items) => { if (active) { setStations(items); setStationDirectoryReady(true); } })
      .catch(() => { if (active) setStationDirectoryReady(false); });
    return () => { active = false; };
  }, []);

  return <section className="content-view view-enter" aria-labelledby="data-title">
    <header className="page-heading"><p className="kicker">Community data</p><h1 id="data-title">Add a reading.<br /><em>Keep it accountable.</em></h1><p>Prepare a canonical field record, sign its content hash with MetaMask, and send it to the community ingest API. Blockchain anchoring is optional and off by default.</p></header>
    <div className="data-layout">
      <aside className={`certificate-card ${wallet ? "certificate-granted" : "certificate-none"}`}><div className="certificate-top"><span className="seal"><Icon name={wallet ? "check" : "shield"} /></span><span className="status-pill">{wallet ? "Signature ready" : "Wallet required"}</span></div><h2>Community issuer identity</h2><p>Connect the wallet that will stand behind this measurement.</p><dl><div><dt>Wallet</dt><dd>{wallet ?? "Not connected"}</dd></div><div><dt>Issuer role</dt><dd>{wallet ? "Checked by API on submit" : "Pending wallet"}</dd></div><div><dt>Station directory</dt><dd>{stationDirectoryReady ? `${stations.length} stations available` : "Awaiting API"}</dd></div></dl>{!wallet && <button className="primary-button dark" onClick={onConnect}><Icon name="wallet" /> Connect wallet</button>}{wallet && <div className="granted-note"><Icon name="check" /> Ready to sign</div>}{walletError && <p className="wallet-error" role="alert">{walletError}</p>}<small>Connecting proves wallet control. The backend still verifies the signature and registered community issuer role before accepting a record.</small></aside>
      <div className={wallet ? "form-card" : "form-card locked"}><div className="form-header"><div><p className="step-label">Water quality record</p><h2>Field measurement</h2></div><span>{wallet ? "Wallet connected" : "Locked"}</span></div><form onSubmit={(event) => void onSubmit(event)}><fieldset disabled={!wallet || isSubmitting}><div className="form-grid"><label className="wide">Site or station name<input required name="site" list="station-list" placeholder="e.g. False Creek East Basin" /><datalist id="station-list">{stations.map((station) => <option value={station.name} key={station.id}>{station.id}</option>)}</datalist></label><label>Observed at<input required name="sampledAt" type="datetime-local" /></label><label>Medium<select required name="medium" defaultValue="water"><option value="water">Water</option><option value="surface_water">Surface water</option><option value="groundwater">Groundwater</option><option value="marine_water">Marine water</option></select></label><label>Collection method<select required name="method" defaultValue="grab"><option value="grab">Grab sample</option><option value="sensor">In-situ sensor</option><option value="lab">Lab analysis</option></select></label><label>Latitude<input required name="latitude" type="number" step="any" min="-90" max="90" placeholder="49.2827" /></label><label>Longitude<input required name="longitude" type="number" step="any" min="-180" max="180" placeholder="−123.1207" /></label></div><div className="measurements-title"><h3>Comparable measurements</h3><span>Community ↔ EMS intersection · leave untested values blank</span></div><div className="metric-grid">{WATER_QUALITY_PARAMETERS.map((parameter) => <label key={parameter.key}><span>{parameter.label}</span><div><input name={parameter.key} type="number" step="any" min="0" placeholder={parameter.placeholder} aria-describedby={parameter.unitNote ? `${parameter.key}-note` : undefined} /><i>{parameter.unit}</i></div>{parameter.unitNote && <small id={`${parameter.key}-note`}>{parameter.unitNote}</small>}</label>)}</div><label className="notes-label">Field notes<textarea name="notes" rows={3} placeholder="Weather, tide, equipment, or anything that helps interpret this sample." /></label><label className="anchor-option"><input name="anchor" type="checkbox" /><span><b>Request blockchain anchor</b><small>Optional. Off by default; the API reports simulated and real anchors distinctly.</small></span></label><div className="submit-row"><p><Icon name="shield" /> Your wallet signs the deterministic SHA-256 content hash.</p><button className="primary-button" type="submit" disabled={isSubmitting}>{submission.phase === "signing" ? "Confirm in MetaMask…" : submission.phase === "submitting" ? "Sending record…" : "Sign and submit"} <Icon name="arrow" /></button></div></fieldset></form>{!wallet && <div className="lock-overlay"><span><Icon name="shield" /></span><b>Wallet needed</b><p>Connect the community issuer wallet to prepare a signature.</p></div>}{submission.phase !== "idle" && <div className={`submission-banner ${submission.phase}`} role={submission.phase === "error" ? "alert" : "status"}>{submission.phase === "error" ? <span className="banner-symbol">!</span> : <Icon name="check" />}<div><b>{submission.phase === "error" ? "Submission stopped" : submission.phase === "unmatched" ? "Accepted, not map-visible" : submission.phase === "submitted" ? "Record accepted" : "Submission in progress"}</b><span>{submission.message}</span>{submission.contentHash && <code>{submission.contentHash}</code>}</div></div>}</div>
    </div>
  </section>;
}

function LeaderboardView() {
  return <section className="content-view leaderboard-view view-enter" aria-labelledby="leaderboard-title">
    <header className="page-heading leaderboard-heading"><div><p className="kicker">Community ledger · All time</p><h1 id="leaderboard-title">Proof of showing up.</h1></div><p>This board recognizes sustained, issuer-verified fieldwork. It confirms contribution history, not whether a reading is true.</p></header>
    <div className="podium">{leaders.slice(0, 3).map((leader) => <article className={`podium-card place-${leader.rank}`} key={leader.rank}><span className="rank-badge">{leader.rank}</span><div className="avatar">{leader.avatar}</div><div><h2>{leader.name}</h2><p>{leader.place}</p></div><strong>{leader.records}<small>verified records</small></strong></article>)}</div>
    <div className="leader-table-wrap"><div className="leader-table-title"><div><h2>Active contributors</h2><p>Ranked by accepted, issuer-signed records</p></div><span>Updated today</span></div><div className="leader-table" role="table" aria-label="Contributor leaderboard"><div className="leader-row leader-labels" role="row"><span>Rank</span><span>Contributor</span><span>Wallet</span><span>Current streak</span><span>Records</span></div>{leaders.map((leader) => <div className="leader-row" role="row" key={leader.rank}><span className="table-rank">{String(leader.rank).padStart(2, "0")}</span><span className="contributor"><i>{leader.avatar}</i><span><b>{leader.name}</b><small>{leader.place}</small></span></span><span className="mono">{leader.handle}</span><span>{leader.streak}</span><strong>{leader.records}</strong></div>)}</div></div>
    <p className="leader-note"><Icon name="shield" /> Rankings will be calculated from backend-verified contributions. Placeholder data is shown for interface development.</p>
  </section>;
}
