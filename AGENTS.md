# AGENTS.md

This file defines the general rules, responsibilities, and working conventions for AI coding agents operating in this repository.

## 1. General Principles

* Prioritize correctness, maintainability, security, and clarity.
* Make the smallest reasonable change required to accomplish the task.
* Preserve existing architecture, conventions, and behavior unless a change is explicitly required.
* Do not introduce unnecessary dependencies, abstractions, or complexity.
* Prefer explicit, readable implementations over clever solutions.
* Do not silently change public APIs, configuration formats, schemas, or externally observable behavior.
* Treat existing tests and documentation as part of the specification.
* When requirements are ambiguous, infer intent from the surrounding code, documentation, and established project conventions.
* Clearly distinguish verified facts from assumptions.

## 2. Agent Roles

An agent may perform one or more of the following roles depending on the task.

### Planner

Responsible for understanding the request and determining the minimum set of changes required.

The Planner should:

* Inspect relevant files before proposing changes.
* Identify affected components and dependencies.
* Consider backward compatibility and possible regressions.
* Avoid expanding scope beyond the requested task.
* Break large changes into logical, verifiable steps.

### Implementer

Responsible for modifying source code and configuration.

The Implementer should:

* Follow repository conventions.
* Keep functions and modules focused.
* Reuse existing utilities before creating new ones.
* Avoid unrelated refactoring.
* Handle expected failure cases explicitly.
* Preserve compatibility unless instructed otherwise.
* Add comments only where they explain non-obvious reasoning.

### Reviewer

Responsible for checking correctness and maintainability.

The Reviewer should verify:

* The implementation satisfies the original requirement.
* No unrelated behavior was changed.
* Edge cases are reasonably handled.
* Security boundaries remain intact.
* Error handling is appropriate.
* Naming and structure are consistent with the repository.
* Tests adequately cover changed behavior.

### Tester

Responsible for validating changes.

The Tester should:

* Run the most relevant tests first.
* Run broader tests when practical.
* Add or update tests for new behavior.
* Test failure and boundary cases where appropriate.
* Report tests that could not be executed.
* Never claim a test passed unless it was actually run.

### Documentation Maintainer

Responsible for keeping documentation synchronized with behavior.

Update documentation when a change affects:

* installation,
* configuration,
* APIs,
* CLI commands,
* environment variables,
* user-facing behavior,
* architecture,
* operational procedures.

Do not create documentation changes for implementation details that users do not need to know.

## 3. Repository Exploration

Before editing code:

1. Read the files directly related to the task.
2. Search for existing implementations of similar behavior.
3. Identify tests covering the relevant functionality.
4. Inspect configuration and dependency files when applicable.
5. Check for more specific `AGENTS.md` files in subdirectories.

Do not assume a component's behavior from its filename alone.

## 4. Scope Control

Agents must remain within the scope of the requested task.

Avoid:

* unrelated cleanup,
* mass formatting,
* speculative optimization,
* renaming unrelated symbols,
* replacing libraries without necessity,
* reorganizing directories without a clear requirement,
* changing generated files when their source should be changed instead.

Small supporting changes are acceptable when they are directly necessary for the requested implementation.

## 5. Code Style

Follow the style already established in the repository.

General expectations:

* Use meaningful names.
* Keep functions reasonably small and focused.
* Avoid unnecessary nesting.
* Prefer straightforward control flow.
* Remove dead code introduced or made obsolete by the change.
* Do not duplicate logic when an appropriate shared abstraction already exists.
* Avoid premature abstraction when code is used only once.
* Preserve formatting conventions used by surrounding files.

If the repository has formatter, linter, or style configuration, that configuration takes precedence.

## 6. Dependencies

Before adding a dependency:

* Check whether the functionality already exists in the standard library or current dependencies.
* Consider the maintenance and security cost of introducing it.
* Prefer well-maintained, established packages.
* Avoid adding large dependencies for trivial functionality.
* Do not upgrade unrelated packages unless necessary.

Dependency lockfiles should be updated when required by the project's package-management workflow.

## 7. Security

Security-sensitive changes require additional care.

Agents must:

* Never hard-code passwords, API keys, tokens, private keys, or other credentials.
* Avoid logging secrets or sensitive user data.
* Validate untrusted input at appropriate trust boundaries.
* Use parameterized queries rather than constructing database queries through unsafe string concatenation.
* Avoid unsafe command execution with untrusted values.
* Preserve authentication and authorization checks.
* Follow least-privilege principles.
* Avoid weakening TLS, certificate validation, sandboxing, access controls, or security checks merely to make something work.
* Treat deserialization, file paths, shell commands, network input, and user-controlled templates as potential attack surfaces.

When a requested change has meaningful security implications, document them in the final summary.

## 8. Error Handling

Errors should be handled at the layer capable of responding meaningfully.

Prefer:

* specific exception types,
* actionable error messages,
* graceful handling of expected failures,
* preserving useful diagnostic context.

Avoid:

* empty catch blocks,
* silently swallowing unexpected failures,
* broad exception handling without justification,
* exposing sensitive internal details to end users.

## 9. Logging

Logging should help diagnose behavior without creating unnecessary noise.

* Use existing logging infrastructure.
* Select appropriate log levels.
* Do not log credentials or sensitive payloads.
* Avoid high-volume logs inside tight loops unless required for debugging.
* Remove temporary debugging output before completing the task.

## 10. Testing

Changes should be accompanied by appropriate validation.

Where applicable:

* Add regression tests for bugs.
* Add tests for newly introduced behavior.
* Test both success and failure paths.
* Keep tests deterministic.
* Avoid reliance on external services when reasonable mocks or fixtures exist.
* Do not weaken existing tests simply to make them pass.

A failing test should be investigated rather than automatically modified.

## 11. Commands and Tooling

Prefer repository-provided commands over custom alternatives.

Examples include:

* project-specific build scripts,
* package-manager scripts,
* Makefiles,
* task runners,
* formatter configurations,
* lint configurations,
* test scripts.

Do not run destructive commands unless explicitly necessary.

Avoid operations such as:

* deleting large directories,
* resetting repositories,
* force-pushing,
* rewriting Git history,
* deleting databases,
* modifying production resources,

unless the task explicitly requires them and the consequences are understood.

## 12. Git Practices

Unless explicitly asked otherwise:

* Do not create commits.
* Do not push changes.
* Do not rewrite Git history.
* Do not modify unrelated working-tree changes.
* Do not discard user changes.
* Keep changes logically grouped.

When inspecting diffs, distinguish pre-existing modifications from changes introduced by the agent.

## 13. Generated Files

Do not manually modify generated artifacts when a source-of-truth file exists.

Instead:

1. modify the source,
2. run the appropriate generator,
3. verify the resulting diff.

Examples include generated API clients, compiled assets, lockfiles, schemas, and documentation generated from source annotations.

## 14. Configuration and Environment

* Maintain compatibility with existing configuration where practical.
* Do not introduce required environment variables without documenting them.
* Provide safe defaults when appropriate.
* Never commit real credentials in example configuration.
* Use clearly fake placeholders in samples.

Example:

```text
API_KEY=your-api-key-here
```

## 15. API Changes

For public APIs:

* Preserve backward compatibility unless a breaking change is explicitly intended.
* Validate inputs.
* Keep response structures stable.
* Document new parameters or behaviors.
* Update relevant tests.
* Consider versioning requirements for breaking changes.

Do not silently reinterpret existing fields in incompatible ways.

## 16. Database Changes

Database modifications should be conservative.

When applicable:

* Use migrations.
* Prefer backward-compatible schema transitions.
* Consider existing data.
* Avoid destructive migrations unless explicitly required.
* Index fields based on demonstrated access patterns rather than speculation.
* Keep transactional boundaries clear.

Migration rollback behavior should be considered when the framework supports it.

## 17. Performance

Do not optimize without evidence, but avoid obvious inefficiencies.

Pay particular attention to:

* repeated network calls,
* N+1 database queries,
* unnecessary full-file or full-table scans,
* unbounded memory growth,
* blocking work in asynchronous execution paths,
* repeated expensive parsing or serialization.

Prefer measurable improvements over speculative micro-optimizations.

## 18. Concurrency and State

When modifying concurrent or asynchronous code:

* Identify shared mutable state.
* Preserve thread/process safety.
* Avoid race conditions.
* Respect cancellation and timeout behavior.
* Ensure resources are released properly.
* Avoid introducing unnecessary global state.

## 19. Comments and Documentation

Comments should explain **why**, not restate obvious code.

Good comments describe:

* non-obvious constraints,
* protocol requirements,
* compatibility decisions,
* security assumptions,
* reasoning behind unusual behavior.

Avoid comments that merely translate code into English.

## 20. Completing a Task

Before considering a task complete:

1. Review the final diff.
2. Confirm the implementation matches the request.
3. Run relevant tests.
4. Run formatting or lint checks when appropriate.
5. Check for accidental unrelated modifications.
6. Update documentation if required.
7. Note any validation that could not be performed.

The final report should briefly state:

* what changed,
* which files or components were affected,
* what validation was performed,
* any known limitations or follow-up concerns.

## 21. Handling Uncertainty

When information is unavailable:

* Inspect the repository before guessing.
* Prefer existing project conventions.
* Make conservative assumptions.
* Avoid inventing APIs, files, commands, or requirements.
* State important assumptions when they materially affect the implementation.

If several approaches are valid, prefer the one requiring the least architectural disruption.

## 22. Instruction Precedence

Agents should follow instructions in this order:

1. Explicit user or task instructions.
2. The nearest applicable `AGENTS.md`.
3. Repository documentation and established conventions.
4. This file's general rules.
5. Reasonable language/framework best practices.

A more specific `AGENTS.md` located deeper in the directory tree overrides conflicting guidance from this file for files within its scope.

## 23. Core Rule

**Understand first, change only what is necessary, verify the result, and leave the repository in a better-defined state than you found it.**

