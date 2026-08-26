# Regulatory Checklist

Mark each row `Y` / `N` / `?`. **"?" is a good answer** — write what we would need
to find out and bring it to the mentor table.

Development has not started yet, so the draft column is a starting point, not a
finding. Re-check it once there is code.

## Part 1 — 14 questions

| # | Question | Draft | If yes or unsure |
| --- | --- | --- | --- |
| 1 | Is any token or unit we issue a security / investment contract? | N | Do we need a token at all? |
| 2 | Do we issue or rely on a stablecoin? | N | Note the issuer regime (Bank of Canada / GENIUS / MiCA EMT). |
| 3 | Have we listed every jurisdiction — users, team, servers, funders? | **?** | Pick one standard or geoblock, and write it down. Servers count separately. |
| 4 | Do we target EU, Korean, or US persons? | N | MiCA needs an EU entity; reverse solicitation is read narrowly. |
| 5 | Do we exchange, transfer, custody, or issue value for others? | N | Partner with a licensee, redesign to be non-custodial, or name the licence. |
| 6 | KYC / travel rule / sanctions screening at on- and off-ramps? | N/A | We have no ramps. Changes the moment anyone is paid. |
| 7 | Are we a crypto-asset service provider under CARF / DAC8? | N | One KYC data model serving AML, tax, and privacy. |
| 8 | Is any personal data on-chain — including a wallet address? | **?** | Keep it off-chain. Anchor a digest only, and be able to explain deletion. |
| 9 | Who holds user or treasury assets? | Nobody | Segregation is non-negotiable if this ever changes. |
| 10 | Do we have a legal wrapper, or are contributors exposed? | **?** | Only matters if this continues past the Blockathon. |
| 11 | Who can upgrade, pause, censor, or profit? | **?** | Minimise discretion we don't need; document the rest. |
| 12 | Forked code — LICENSE read, attribution kept? | N/A | MIT, Apache, and GPL carry real conditions. |
| 13 | Who owns what we build this week — team, UBC, or sponsor? | **?** | Find the university IP policy in writing. |
| 14 | Risk disclosure, incident plan, named accountable person? | **?** | Name a person, not a role. |

Six rows are open: **3, 8, 10, 11, 13, 14**. Those are the conversation.

## Part 2 — Legal outcomes (Greenwood method)

1. **Who is involved** — roles, parties, technical actors, and what each one does.
2. **What the legal dynamics are** — rights and duties, causes of action, recourse
   on-chain and off-chain.
3. **Which 2026 regulator each actor answers to.**

Key question: can we prove **who** signed, **with what intent**, on a record whose
chain of custody holds?

---

Current to August 2026. Educational, not legal advice.
