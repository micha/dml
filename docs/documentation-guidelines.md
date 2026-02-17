# Documentation Writing Guidelines

Status: Active guidance.

This document defines how repository docs should be written and maintained.

## 1. Goals

- Keep docs accurate, scannable, and easy to maintain.
- Keep one clear source of truth per concept.
- Minimize drift by referencing authoritative docs instead of duplicating rules.

## 2. Source-of-Truth Rules

- Assign each important concept to one authoritative document.
- In non-authoritative docs, link to the authority instead of mirroring details.
- Only restate behavior outside the source-of-truth doc when needed for local
  readability.
- If behavior differs from the source of truth, document only the exception.

## 3. Authority Boundary Section

Major spec docs should include an "Authority boundary" section near the top.

Use this pattern:

- "This document is authoritative for <owned topics>."
- "For <other topic>, see <authoritative doc>."

Keep this section short and explicit.

## 4. Normative vs Informative Content

- Mark normative behavior clearly.
- Mark examples, sketches, and pseudocode as informative.
- Use RFC 2119 keywords (MUST, SHOULD, MAY) only for normative requirements.

## 5. Cross-References

- Prefer direct file + section references (for example,
  `docs/spec/object-model.md` Section 10).
- Reference concepts where they are defined, not where they are merely used.
- When replacing duplicated text, keep a concise local summary and point to the
  authoritative section.

## 6. Writing Style

- Use precise language and stable terminology.
- Prefer short sections and bullet lists.
- Keep examples concrete and minimal.
- Avoid vague words like "usually" or "generally" when requirements are strict.
- Keep tense and wording consistent across related docs.

## 7. Change Process

When behavior changes:

1. Update the authoritative document first.
2. Update dependent docs to reference the new/updated section.
3. Remove stale mirrored guidance.
4. Add exception notes only where behavior intentionally differs.

When adding a new concept:

1. Decide and document the source-of-truth location.
2. Add or update authority-boundary references in related docs.
3. Add a short entry in `docs/spec/overview.md` if it affects spec navigation.

## 8. Consistency Checklist

Before finishing doc changes, verify:

- Each concept has one clear source of truth.
- No duplicated normative rules exist across docs.
- Authority boundary sections are present and up to date.
- Cross-references point to correct files/sections.
- Exceptions are explicit, minimal, and justified.

## 9. Current Canonical Ownership (Spec Suite)

- Packed-record model, encoding, hashing, keyspace, validation:
  `docs/spec/object-model.md`
- Execution lifecycle, caching/retries, in-flight policy, and execution
  adapters: `docs/spec/execution.md`
- Remotes, transfer protocol, and remote adapters:
  `docs/spec/remotes.md`
- CLI command contract and CLI-facing behavior:
  `docs/spec/cli.md`
- Python API surface and binding behavior:
  `docs/spec/python-bindings.md`
- Spec navigation and concept-to-source map:
  `docs/spec/overview.md`
