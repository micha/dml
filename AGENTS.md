# Agent Guide

## MANDATORY: Use td for Task Management

Run td usage --new-session at conversation start (or after /clear). This tells you what to work on next.

Sessions are automatic (based on terminal/agent context). Optional:
- td session "name" to label the current session
- td session --new to force a new session in the same context

Use td usage -q after first read.

Use this guide for planning, design, and build/test decisions.

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
- For C/C++ use `clang-format`; add a `.clang-format` file at repo root when you
  introduce formatting rules.
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
- Prefer Python property/integration tests for CLI behavior; keep C tests only
  when low-level fault injection or internal hooks are required.
- Use descriptive test names that capture the behavior.
- Keep fixtures small and local to the test when possible.
- Always run `scripts/check.sh` after modifying, creating, or deleting source or
  test files.
- Coverage reports are generated at `coverage-report/` (C).

### Security and Secrets

- Never commit secrets, keys, or credentials.
- Store local secrets in ignored files like `.env`.
- Mask or omit sensitive values from logs and error messages.
- Treat config or schema changes as security-sensitive.

### Collaboration

- Keep diffs focused; avoid unrelated reformatting.
- Prefer consistent terminology across code, docs, and tests.
- Leave TODOs with an owner or clear next step.
- This repo is local-only (no remotes configured); do not push or open PRs.
- Do not push from the VM; pushes happen out-of-band from the host.

## Commit Messages

- Use a short imperative title (50-72 chars) plus a body that explains the why.
- Prefer a 1-2 sentence body that captures intent and scope.
- Wrap commit message body lines at 80 characters or less.
- When asked to draft a commit, follow this format:
  - Title: concise summary of the change
  - Body: 1-2 sentences on motivation and impact
- Split commits when uncommitted changes include multiple, clearly differentiated tasks.

## API Stability

- Headers under `include/dml/` define the public C API; changes should be
  additive when possible and coordinated with versioning.

## Documentation Expectations

- Document new modules with a short overview and usage example.
- Keep README or docs updated when commands or configuration change.
- Include links to external systems or services when relevant.

## OpenCode Slash Commands

- Define OpenCode slash commands as Markdown files under `.opencode/commands/`.
- Use YAML frontmatter for metadata like `description` and `model`, then put the
  command prompt body below the frontmatter.

## Build, Lint, and Test Commands

All commands assume a build directory at `build/` and Meson as the build
system.

Prerequisites (verify on your system):

- Meson (`meson --version`)
- clang-format (`clang-format --version`)
- valgrind (`valgrind --version`) for memcheck targets
- lcov + genhtml for coverage reports

- Configure: `meson setup build`
- Configure (debug): `meson setup build-debug --buildtype=debug`
- Build (all targets): `meson compile -C build`
- Build (single target): `meson compile -C build <target>`
- Format (single file): `clang-format -i path/to/file.c`
- Format (project C/C++): `meson compile -C build format`
- Format check (project C/C++): `meson compile -C build format-check`
- Test (Python): `python3 -m pytest tests/python`
- Test (single file): `python3 -m pytest tests/python/test_cli_properties.py`
- Run CLI (built): `build/dml <args>`
- Static library output: `build/libdml.a`
- Full check (rebuild/test/format-check/coverage): `scripts/check.sh`
  (use `scripts/check.sh -f` to wipe build artifacts first)
- Full check with valgrind: `scripts/check.sh -v`

Memory checking (valgrind):

- Run tests under valgrind:
  ```sh
  meson test -C build --wrapper \
    'valgrind --leak-check=full --error-exitcode=1'
  ```
- Direct run: `valgrind --leak-check=full --error-exitcode=1 build/dml`

Coverage (gcov + lcov):

- Configure coverage build:
  `meson setup build-coverage -Db_coverage=true --buildtype=debug`
- Build + run tests:
  `meson compile -C build-coverage && meson test -C build-coverage`
- Capture coverage:
  `lcov --capture --directory build-coverage --output-file coverage.info`
- HTML report: `genhtml coverage.info --output-directory coverage-report`
- Coverage thresholds enforced by `scripts/check.sh`: 80% line / 70% branch for
  C. Exclusions are configured in `.lcovrc`.

When documenting new tooling, include:

- The exact command line to run from repo root.
- Expected runtime for the full test suite.
- Required environment variables and sample values.
- How to run a single test file, module, or test case.
- How to run lint or format checks on a single file.
- Any setup steps that must happen before running commands.

When changing behavior, update the source-of-truth doc first:
- Packed records/storage/hashing/validation -> docs/spec/object-model.md
- Execution lifecycle/remotes/adapters -> docs/spec/execution-and-remotes.md
- CLI contract/errors/exit codes -> docs/spec/cli.md
- Python binding surface and behavior -> docs/spec/python-bindings.md


## Updating This File

Keep this guide current whenever you add tooling or conventions. Add new
sections rather than overloading existing ones, and prefer concrete commands
over general advice. If you add Cursor or Copilot rules, summarize them here
and reference their locations.

## See Also

- Architecture overview: `docs/architecture.md`
- Spec overview: `docs/spec/overview.md`
