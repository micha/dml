# Agent Guide

## Code Style Guidelines

These guidelines reflect the current codebase conventions. If you add a
formatter or linter, defer to its rules and update this section accordingly.

### General

- Prefer small, well-scoped changes with clear intent.
- Keep functions short and single-purpose.
- Favor explicitness over cleverness; write for readability first.
- Avoid global mutable state and hidden side effects.
- Keep error messages actionable and specific.
- Validate inputs at module boundaries.

### Formatting

- Use a formatter when available (e.g., Prettier, Black, gofmt, rustfmt).
- Indent C code with 2 spaces; do not use tabs.
- Use K&R braces: opening brace on the same line as the declaration.
- Keep blank lines meaningful: separate include blocks and logical sections.
- Limit line length to 100-120 characters unless the ecosystem dictates
  otherwise.
- Prefer early returns to reduce nesting.

### Imports and Modules

- Group imports by standard library, third-party, then local modules.
- Sort alphabetically within each group unless the language recommends
  otherwise.
- Avoid circular dependencies.
- Prefer explicit imports over wildcard/glob imports.
- Remove unused imports promptly.
- Keep module boundaries clear; avoid deep cross-module reach.
- For C headers/sources, separate system includes from project includes with a
  blank line.

### Types and Interfaces

- Use types/interfaces to document intent and boundary shapes.
- Prefer narrow types over broad `any`-style types.
- Use explicit return types for public APIs.
- Keep type definitions close to where they are used, unless shared broadly.
- Favor immutable data where the language supports it.
- Use header guards with uppercase names and no trailing comments on `#endif`.

### Naming Conventions

- Use descriptive, domain-focused names.
- Prefer `verbNoun` for functions and `noun` for data structures.
- Avoid single-letter names except for trivial scopes (e.g., `i` in loops).
- Keep abbreviations consistent and well-known.
- Use names that reflect units (e.g., `timeoutMs`, `maxRetries`).

### Error Handling

- Fail fast with clear error messages when invariants are violated.
- Wrap lower-level errors with context at module boundaries.
- Avoid swallowing errors; log or return them explicitly.
- If using exceptions, catch only what you can handle.
- Include remediation hints in errors when practical.

### Logging and Observability

- Log at the boundary between external input and internal logic.
- Avoid logging sensitive data.
- Use structured logs if the stack supports it.
- Keep log levels consistent (debug/info/warn/error).

### Testing

- Add tests for new behavior or bug fixes.
- Keep tests deterministic; avoid time-dependent flakiness.
- Prefer unit tests for pure logic; use integration tests for boundary
  interactions.
- Prefer Python Hypothesis property-based tests for Python bindings and CLI
  behavior.
- Keep C tests focused on low-level scenarios (for example fault injection or
  internal hook validation).
- Use Mull mutation testing to validate test effectiveness.
- Use lcov/gcov for line, function, and branch coverage tracking; target 100%
  coverage.
- Use coverage.py for Python source coverage; target 100% line coverage.
- Coverage is a means of improving assurance, not an end in itself. The user
  authorizes narrow exclusions for precise lines/branches/regions where exercising
  them adds no useful assurance (for example proven-unreachable defensive edges or
  dependency/compiler-generated code). Record each excluded location and its
  reasoning in delivery notes; distinguish excluded code from tested code.
- Add meaningful boundary/error and allocation-failure tests. Difficulty alone
  does not justify an exclusion. Do not hide real behavior or bugs, lower the
  remaining coverage thresholds, or treat skipped/failing checks as passed.
  New exclusions that do not meet this no-value policy need a user decision.
- [Coverage scope and exclusions](tests/coverage-exclusions.md) catalogs the exact
  markers and their invariants. The private fault-test core substitutes dependency
  calls only in test builds; do not add fault state to the installed library.
- Use Valgrind for memory checks when requested or when touching memory-critical
  code paths.
- Use `scripts/check.sh` as the standard end-to-end validation entrypoint.
- CI uses `scripts/check.sh -c` to report coverage without percentage gates;
  see `README.md` (Build and Test) for validation modes and Windows dependencies.
- Use descriptive test names that capture the behavior.
- Keep fixtures small and local to the test when possible.

### Security and Secrets

- Never commit secrets, keys, or credentials.
- Store local secrets in ignored files like `.env`.
- Mask or omit sensitive values from logs and error messages.
- Treat config or schema changes as security-sensitive.

### Collaboration

- Keep diffs focused; avoid unrelated reformatting.
- Prefer consistent terminology across code, docs, and tests.
- Leave TODOs with an owner or clear next step.

## Commit Messages

- Use a short imperative title (50-72 chars) plus a body that explains the why.
- Use markdown for the body where appropriate.
- Split commits when uncommitted changes include multiple, clearly differentiated tasks.

## API Stability

- Public API changes should be additive when possible and coordinated with
  versioning.

## Documentation Expectations

- Before modifying any documentation file (for example `docs/**/*.md`), read
  `docs/documentation-guidelines.md` in the current session.
- Follow `docs/documentation-guidelines.md` for writing style, source-of-truth
  ownership, and cross-reference patterns.
- Document new modules with a short overview and usage example.
- Keep README or docs updated when commands or configuration change.
- Include links to external systems or services when relevant.

## OpenCode Slash Commands

- Define OpenCode slash commands as Markdown files under `.opencode/commands/`.
- Use YAML frontmatter for metadata like `description` and `model`, then put the
  command prompt body below the frontmatter.

## Tooling and Layout

Tooling and project layout guidance is being rewritten from scratch.
Do not treat prior command examples or directory assumptions as canonical.


## Updating This File

Keep this guide current whenever you add tooling or conventions. Add new
sections rather than overloading existing ones, and prefer concrete commands
over general advice. If you add Cursor or Copilot rules, summarize them here
and reference their locations.

## See Also

- Architecture overview: `docs/architecture.md`
- As-built spec orientation: `docs/spec-next/README.md`
- Old draft spec overview: `docs/spec/overview.md`
