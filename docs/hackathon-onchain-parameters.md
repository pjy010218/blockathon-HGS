# Hackathon: On-chain Water Quality Audit Trail (SDG 14)

Community-auditable audit trail for water quality measurement data. Measurement logs are cryptographically hashed and timestamped on-chain so factories or authorities cannot secretly alter or withhold data after the fact.

**Datasets**

| Role | File | Notes |
|---|---|---|
| Community / coastal | `dataset_download_5399.csv` | Fraser Riverkeeper / Swim Drink Fish, False Creek (2019) |
| Authority / industry | `this_yr_sample_comparable.csv` (from `this_yr.csv`) | BC EMS; waste/fresh/outfall-heavy |

---

## What belongs on-chain

Keep it minimal — only what proves integrity:

- **Hash** of the canonical measurement (e.g. SHA-256)
- **Timestamp** (observation time)
- **Station ID** / location
- **Source** (`community` \| `authority` / `industry`)
- Optional: parameter code(s) or batch ID

**Not on-chain:** full raw CSVs or large payloads.

Off-chain = full raw data. On-chain = hash + metadata → later change = hash mismatch.

---

## Parameters to use

Use the **intersection** of Community ↔ EMS, normalized to canonical names/units:

| Parameter | Community (`dataset_download_5399`) | EMS (`this_yr`) | Canonical unit |
|---|---|---|---|
| pH | `ph (std_units, …)` | `0004` / `PH-F` | `pH` (dimensionless) |
| Dissolved oxygen | `oxygen (mg_l, …)` | `DO-F` | `mg/L` |
| Conductivity | `conductivity (us_cm, …)` | `0011` / `EC-F` | `µS/cm` |
| Water temperature | `water_temperature (deg_c, …)` | `TEMF` | `°C` |
| Nitrate | `nitrates (mg_l, …)`* | `1110` | `mg/L` |
| Nitrite | `nitrites (mg_l, …)`* | `1111` | `mg/L` |
| Hardness | `hardness (mg_l, …)`* | `1107` | `mg/L` (as CaCO₃) |
| E. coli | `e_coli (cfu_per_100ml, …)` | `0147` | `CFU/100mL` (or note `MPN/100mL`) |

\* Only partially filled in the community set (~26/74 rows).

**Optional / demo-only (one side):** Salinity (community, `ppm`/`ppt`) — little/no EMS match.

**Do not use:** EMS `TDST` as TDS — that code is dustfall, not water total dissolved solids.

---

## Canonical measurement shape (hash input)

### Single-parameter record

```json
{
  "station_id": "OlympicVillage",
  "lat": 49.27237,
  "lon": -123.10345,
  "observed_at": "2019-06-05T17:00:00-07:00",
  "source": "community",
  "medium": "marine",
  "parameter": "pH",
  "value": 8.01,
  "unit": "pH",
  "qa_status": "Needs review"
}
```

### Multi-parameter sample (recommended for hackathon)

One hash per sampling event — matches community row shape; group EMS long-format by `Location` + `DateTime` + `Activity` first.

```json
{
  "station_id": "OlympicVillage",
  "observed_at": "2019-06-05T17:00:00-07:00",
  "source": "community",
  "medium": "marine",
  "readings": [
    {"parameter": "pH", "value": 8.01, "unit": "pH"},
    {"parameter": "dissolved_oxygen", "value": 9.37, "unit": "mg/L"},
    {"parameter": "conductivity", "value": 21764, "unit": "µS/cm"},
    {"parameter": "temperature", "value": 17.0, "unit": "°C"},
    {"parameter": "e_coli", "value": 13.66, "unit": "CFU/100mL"}
  ]
}
```

---

## Demo caveats

- **Geography:** No EMS hits at the three False Creek sites — compare regionally (Lower Mainland / Burrard) or mock community stations near EMS outfalls.
- **Time:** Community source years are 2019; EMS is 2024–2026. The demo seed shifts each series so it **ends in 2025** (spacing preserved; original dates stay in `raw_payload`).
- **Medium:** Community = ocean/marine; EMS sample = mostly waste/fresh — always store `medium` in the hashed payload.

---

## Alignment with *Blockathon for Social Good 2026* (slides)

Source: `Blockathon_for_Social_Good_2026.pptx` — focal SDG **14 · Life Below Water** (slide 8).

### Presentation challenge (Goal 14)

| # | Slide wording | Our concept / data |
|---|---|---|
| 1 | **Industrial pollution · verify runoff reporting** | EMS `this_yr` / sample: `Water - Waste`, Outfalls, Permittee sites → industry/authority feed hashed on-chain |
| 2 | **Coastal accountability · expose under-reporting** | Community vs. authority comparison; missing/altered reports → hash mismatch or absent on-chain commit |
| 3 | **Community confidence · make methods legible** | Canonical JSON (parameter + value + unit + medium + QA); citizen data from `dataset_download_5399` |

Slide framing: *“Evidence communities can verify”* + *“Evidence must be trustworthy and governance must protect affected communities.”*

| Presentation theme | Fit |
|---|---|
| Core problem: **trust** between citizens, corporations, governments (slide 4) | Strong — dual feeds (community + EMS) are exactly those actors |
| Blockchain for **verifiable evidence**, not generic storage | Strong — hash + timestamp; raw data off-chain |
| Use AI **when it strengthens** the solution (slide 3) | Optional — e.g. anomaly / under-reporting detection; not required for MVP |
| Deliverable: smart contract **or** AI agent demo + pitch with **Three Layer Model** (slide 10) | Plan: smart-contract audit trail as minimum; pitch maps problem → mechanism → outcome |
| Judging: problem value, security/privacy, usability, feasibility (slide 14) | Hash-only on-chain helps privacy; keep UI simple (verify / mismatch) |

### Gaps to address for a strong pitch

1. **Methods legible (point 3):** Show *how* a sample was taken (device/method field), not only values — community has form/QA notes; EMS has `Analysis_Method` / `Collection_Method`. Put a method digest in the hashed payload.
2. **Governance / affected communities:** Who may submit? Who disputes? Sketch roles (community station, regulator, plant) even if the contract is simple.
3. **Privacy:** Prefer hashes + minimal metadata on-chain; avoid dumping full personal field-participant names from EMS.
4. **Demo honesty:** Call out geo/time mismatch of the two CSVs; frame as prototype feeds, not live co-located sensors.

### Pitch one-liner (maps to slide 8)

> Community and industrial water readings are normalized, hashed, and timestamped on-chain so runoff reporting can be verified, under-reporting exposed, and measurement methods remain auditable by coastal communities.

---

## Alignment with *Updated 2026 Blockathon Judging Rubric*

Source: `Updated 2026 Blockathon Judging Rubric.xlsx` — scale **1–5** per criterion (5 = highest).

| # | Criterion | Likely level today | Target | What to show in prototype + pitch |
|---|---|---|---|---|
| 1 | **Comprehensiveness** — how completely the solution addresses the challenge | **3–4** | **5** | Rubric explicitly mentions addressing the challenge for **both datasets**. Demo must ingest **community CSV + EMS sample**, normalize parameters, hash both feeds, and show at least one **mismatch / missing commit / under-reporting** scenario. |
| 2 | **Context & relevance** — understanding of technical, data/records, social context | **4** | **5** | Cite SDG 14 slide 8, BC EMS + Fraser Riverkeeper context, who the actors are (community / plant / regulator). Acknowledge geo/time/medium differences honestly. |
| 3 | **Economic & social benefit** | **3–4** | **5** | Social: coastal trust, accountability for runoff. Economic: lower audit cost, faster dispute resolution, fewer opaque compliance reports. Name a **buyer/user** (NGO, municipality, community org). |
| 4 | **Security & privacy** | **4** | **5** | Hash-only on-chain; raw CSV off-chain/IPFS optional. No personal names from EMS on-chain. Address **spoofing**: signed submissions or role-based keys; optional device/method attestation in hash payload. |
| 5 | **Usability & convenience** | **3** | **4–5** | One-screen flow: upload sample → see on-chain commit → “Verify” / “Mismatch” / “Not reported”. Avoid blockchain jargon in the UI. |
| 6 | **Feasibility** — operational, technical, legal, social, economic | **3** | **4–5** | **Technical:** strong (smart contract + CSV pipeline). **Operational:** pilot at 3 community stations + regional EMS feed. **Legal/social:** data stewardship, who can dispute. **Economic:** public-good / grant-funded monitoring — say so explicitly. |
| 7 | **Creativity & presentation** | **3–4** | **5** | Story arc: under-reporting pain → dual audit trail → live hash verify. Polish deck; 10-min pitch + demo in &lt;2 min. |

### Rubric wording ↔ our solution (detail)

**Comprehensiveness (Level 5 = “fully addresses the challenge for both datasets”)**

- Community set → coastal / citizen monitoring (SDG 14 point 3: legible methods).
- EMS sample → industrial waste / outfall reporting (points 1–2: verify runoff, expose under-reporting).
- **Gap:** without a working end-to-end demo on **both** files, judges may cap at Level 3 (“partially … one dataset”).

**Context & relevance (Level 5 = excellent technical + data/records + social context)**

- **Technical:** canonical JSON, SHA-256, smart contract `submitMeasurement(hash, meta)`.
- **Data/records:** EMS long-format → sample events; EMS codes mapped to pH, DO, conductivity, etc.
- **Social:** affected coastal communities (False Creek narrative); reference Swim Drink Fish / BC EMS in slides.

**Economic & social benefit (Level 5 = very strong case)**

- *Social:* communities can verify official/industrial claims; reduces information asymmetry (core Blockathon trust theme).
- *Economic:* cheaper than third-party audits; reusable attestation for compliance reporting.
- **Improve:** one slide on “who pays / who adopts” (e.g. Fraser Riverkeeper + municipal open-data mandate).

**Security & privacy (Level 5 = very high standard)**

- Already aligned: minimal on-chain payload.
- **Judges will ask (see 2025 examples in rubric):** GPS/spoofing analog → fake water readings. Answer: signed oracle keys, method metadata in hash, optional multi-party attestation (community + lab).

**Usability (Level 5 = sophisticated + references)**

- Benchmark: strong 2025 teams had clear customer flow + working demo (rubric notes: Penny Arena UX gaps scored 3.5).
- **Must-have:** “Verify integrity” button and plain-language mismatch explanation.

**Feasibility (Level 5 = feasible on all dimensions)**

| Dimension | Assessment |
|---|---|
| Technical | High — hash + contract + CSV ETL is hackathon-realistic |
| Operational | Medium — needs station onboarding & feed agreement |
| Legal | Medium — public EMS data OK; clarify liability of community readings |
| Social | High — fits SDG 14 + trust narrative |
| Economic | Medium — articulate sustainability beyond hackathon |

**Creativity & presentation (Level 5 = very innovative + professional pitch)**

- Novelty: dual-source **community vs authority** audit trail (not generic “data on blockchain”).
- **Risk:** sounding like storage-only chain project — always tie to **tamper detection** and **under-reporting exposure**.

### Score checklist before judging (self-audit)

- [ ] Both datasets loaded in demo
- [ ] At least 8 shared parameters normalized (see table above)
- [ ] Live hash submit + verify + one tamper/mismatch scenario
- [ ] SDG 14 + trust problem stated in first 60 seconds
- [ ] Security (privacy + spoofing) addressed in Q&A slide
- [ ] Pilot / rollout / who benefits slide (rubric rewards this — cf. AttendChain 5/5 notes)
