# Recommended Guidelines

Rules to build by, so the answers in [checklist.md](checklist.md) stay clean.
Written before development starts — following these keeps most of the checklist at
"No", which is the easy place to be.

## 1. Don't move value

Testnet only. No token, no rewards for contributors, no fees, no treasury, no
deposits from anyone outside the team. This one rule is what keeps questions 1, 2,
5, 6, 7, and 9 answered "No".

If someone proposes a contribution reward or a data bounty, that reopens the
checklist. Bring it back here first.

## 2. Keep personal data off-chain

- Anchor a **hash only**. Payloads stay off-chain.
- No names, emails, or wallet addresses of individuals on-chain. "It's only a
  wallet address" and "it's hashed" are both rejected by the EDPB's July 2026
  guidelines.
- Careful with on-chain identifiers that point back to a person — a source record
  ID for a community submission can identify the volunteer who made it.
- A hash of a low-entropy record can be brute-forced. If the record is small,
  anchor a salted digest and keep the salt off-chain.
- Be able to answer: **what happens when someone asks us to delete their data?**
  The answer should be "we delete the off-chain record and the on-chain entry
  points at nothing."

## 3. Keep control points few, and name them

- No owner, upgrade path, pause function, or fee switch in the contract unless
  there is a reason. Not having them is a strong answer.
- Trade-off to accept knowingly: without an upgrade path, a bug means deploying a
  new contract, not editing an old one.
- Write down who holds the deploy key, who runs the API, and who runs the
  frontend. These are control points whether we name them or not.
- "It's decentralised" is not a defence. Someone on the team can intervene — say
  who.

## 4. Say what the system actually proves

- An anchor proves a record **has not changed** since it was anchored. It does not
  prove the measurement is true, the sensor was calibrated, or the source was
  complete.
- Never present a simulated transaction as a real one. Label simulated, pending,
  failed, and confirmed distinctly.
- Don't rank sources or imply one is more trustworthy — that is both a product
  rule and a liability question.

## 5. Watch the licences

- Read the LICENSE of anything we fork or reuse, and keep attribution. MIT,
  Apache, and GPL all carry real conditions.
- Open-sourcing permanently forecloses trade-secret protection. Fine for a
  public-good project, but it is a one-way door.
- Check the UBC IP policy in writing before anyone plans to commercialise this.

## 6. Write down what we don't know

An unresolved question recorded in the repo is worth more than a confident wrong
answer. "Here is the licence we would need, here is the partner we would use, here
is what we would test first" beats claiming we are compliant.

## Name one person

Before the end of the week, one named person accepts accountability — a person,
not a role. If nobody is accountable, regulators tend to make everybody
accountable.
