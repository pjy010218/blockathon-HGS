# Developer Guide

This guide defines the development rules for the Water Audit Trail project.

The project exists to make water-quality records easier to inspect and later changes easier to detect. It must preserve source context and present evidence neutrally. Developers must not introduce features that rank sources, assign trust scores, or tell users which dataset to believe.

## 1. Git and branch workflow

- Never develop directly on `main`.
- Always create a feature, fix, chore, or documentation branch first.

  ```bash
  git switch main
  git pull --ff-only
  git switch -c feature/short-description
  ```

- Keep branches focused on one logical change.
- Do not commit generated files, virtual environments, dependency caches, secrets, or local databases.
- Open a pull request before merging into `main`.
- Do not merge a pull request with failing tests or unresolved review comments.
- Prefer small, reviewable commits.
- Use imperative commit messages, for example:

  ```text
  Add neutral field comparison endpoint
  Preserve upstream dataset identifiers
  Update local development guide
  ```

- Before opening a pull request, rebase or update from `main` and resolve conflicts locally.
- Do not force-push a shared branch. Force-push is acceptable only on a personal feature branch and only when it will not discard another developer's work.

## 2. Naming and formatting

Use descriptive names. Avoid unexplained abbreviations.

### General naming rule

Use camel case for application-level names unless the language or protocol requires another convention:

- TypeScript variables and functions: `recordHash`, `compareRecords`
- React components and classes: `ComparisonPanel`, `BlockchainService`
- JSON fields and API payloads: use the existing API convention consistently

### Python

Follow standard Python conventions:

- Functions, variables, and modules use `snake_case`.
- Classes use `PascalCase`.
- Constants use `UPPER_SNAKE_CASE`.
- Keep API JSON field names stable once published. If an external API requires camel case, model the conversion explicitly instead of mixing conventions internally.

Examples:

```python
content_hash = calculate_hash(payload)

class WaterQualityRecord:
    pass
```

### TypeScript and React

- Variables, functions, and props use `camelCase`.
- Components, types, and interfaces use `PascalCase`.
- Constants use `UPPER_SNAKE_CASE` when they are truly constant configuration values.
- Use explicit types for API responses and shared data structures.
- Do not use `any` unless there is a documented boundary reason.

Examples:

```typescript
const recordHash = calculateRecordHash(payload);

export function ComparisonPanel() {
  return null;
}
```

### Solidity

- Functions and variables use `camelCase`.
- Contracts, structs, and events use `PascalCase`.
- Constants use `UPPER_SNAKE_CASE`.
- Keep contracts small and auditable.

## 3. Data integrity rules

These rules are mandatory because the project's purpose depends on preserving evidence.

- Never overwrite an ingested source record in place.
- Treat a correction as a new version or new record while retaining the earlier record.
- Always retain source provenance, including provider, dataset ID, source record ID, source URL, retrieval time, and relevant method metadata.
- Always retain the original upstream payload in `raw_payload` or an equivalent durable field.
- Never silently discard an upstream field because it does not have a canonical mapping.
- Never convert a missing field into zero, an empty string, or an assumed value.
- Do not silently coerce units, timestamps, locations, or measurement values.
- If normalization is necessary, retain both the normalized value and the original value.
- Hash deterministic content only. Hashing must use a documented canonical serialization.
- Do not include volatile fields such as database IDs or ingestion timestamps in a content hash unless the design explicitly requires it.
- Never represent a simulated blockchain transaction as a real Ethereum transaction.
- Clearly label simulated, pending, failed, and confirmed blockchain states.

## 4. Neutral presentation rules

The application displays records and relationships; it does not decide which source is truthful.

- Do not add trust scores, credibility rankings, “best source” labels, or automatic source recommendations.
- Use descriptive comparison labels such as `same_value_and_unit`, `different_value_or_unit`, and `missing_from_government`.
- Keep government and community values visible side by side.
- Preserve differences caused by missing fields, different units, different sampling times, different locations, or different methods.
- Avoid language such as “correct,” “false,” “better,” or “more trustworthy” unless it is explicitly part of the source's own published metadata and is clearly attributed.
- Explain comparison logic in the UI when needed so users understand that a difference is not automatically a contradiction.

## 5. Backend rules

- Keep route handlers thin; place hashing, comparisons, source integration, and blockchain logic in services or adapters.
- Validate all external input with typed Pydantic models.
- Return stable, documented error responses.
- Use UTC timestamps for stored and exchanged timestamps.
- Never log secrets, private keys, wallet credentials, or complete sensitive payloads.
- Do not make external API calls inside a database transaction unless the failure and retry behavior are defined.
- Source adapters must be isolated from presentation logic.
- Add tests for every new normalization rule and every new comparison status.
- The current in-memory store is for the MVP only; production work must use durable storage and define versioning behavior.

## 6. Frontend rules

- Keep API types centralized and synchronized with the backend schema.
- Show loading, empty, error, and unavailable-source states.
- Do not hide a field merely because it is absent from one source.
- Do not imply that a blockchain anchor validates the truth of the measurement; it validates the integrity of the anchored content.
- Keep wallet connection and blockchain actions explicit and user initiated.
- Never request a wallet signature or transaction without explaining what is being signed or submitted.
- Keep accessibility in mind: semantic tables, labels for controls, keyboard navigation, and readable contrast are required.

## 7. Blockchain rules

- Store hashes and minimal provenance on-chain; keep large source payloads off-chain unless there is a specific reason to do otherwise.
- The on-chain record must be sufficient to locate and verify the corresponding off-chain record.
- Never modify an existing anchor. Corrections must create a new anchor and retain the prior one.
- Record the network, contract address, transaction hash, and block number when available.
- Treat transaction confirmation as asynchronous.
- Never store private keys in the repository, frontend bundle, `.env` files committed to Git, or CI logs.
- Use environment variables or a managed secrets system for RPC URLs and signing credentials.
- Review smart-contract changes separately from ordinary frontend or backend changes.

## 8. Testing requirements

At minimum, run the following before opening a pull request:

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python -m compileall -q app tests
```

When Node.js is installed:

```bash
cd frontend
npm install
npm run build
```

New code should include tests for:

- Hash stability and verification failures.
- Missing fields and source-specific fields.
- Different units, methods, timestamps, and locations.
- Source adapter mappings and preservation of raw payloads.
- API validation and error cases.
- Blockchain states, including simulated and failed transactions.
- UI empty, loading, error, and comparison states where practical.

## 9. Pull request checklist

Before requesting review, confirm:

- [ ] The change is on a non-`main` branch.
- [ ] Tests and relevant builds pass.
- [ ] The change preserves source provenance and raw data.
- [ ] Missing fields remain distinguishable from zero or equal values.
- [ ] No trust ranking or unsupported interpretation was added.
- [ ] API or schema changes are documented.
- [ ] Blockchain behavior is accurately labeled.
- [ ] No secrets or generated files are included.
- [ ] README or relevant documentation is updated.
- [ ] The pull request explains what changed, how it was tested, and any known limitations.

## 10. Handling disagreements

When developers disagree about a data transformation or UI interpretation, prefer the approach that preserves more source context and makes fewer assumptions. Record unresolved design decisions in an issue or architecture note rather than hiding the disagreement in an opaque transformation.
