# Agent instructions for the as-built specification

Read the repository [AGENTS.md](../../AGENTS.md),
[Documentation Writing Guidelines](../documentation-guidelines.md) completely,
and this specification's [README.md](README.md) before modifying this directory.
Read the shared [glossary](glossary.md) for terminology.

## Scope

- This directory describes functionality actually implemented for the evolving
  new direction. It is not an approval to implement the rest of the design.
- Documented functionality defines the implemented scope. Do not maintain a
  separate missing-feature inventory or future-feature roadmap in this spec.
- Inspect sources, public headers and relevant tests before changing a technical
  contract. Enum constants, old draft specs and design notes alone are insufficient
  evidence of implementation.
- Keep the existing `docs/spec/` suite untouched unless separately authorized.
  Its future layers are not automatically requirements for this specification.
- Design discussions, iteration plans and open questions belong in the separate
  design repository. A concise orientation link is appropriate; speculative
  normative APIs and placeholder subsystem specifications are not.

## Ownership and change procedure

- Apply the shared guidelines: one owning document per concept, authority boundaries
  near the top, direct section references, concise prose and explicitly informative
  examples.
- Use glossary vocabulary consistently in maintained documentation. Define a new
  term or explicitly qualify a local one instead of silently changing meanings.
  Glossary entries, including provisional ones, do not establish implementation.
- Use RFC 2119 keywords only for implemented technical contracts, not plans.
- Maintain the README's concept map, documented scope and Mermaid diagram when
  adding or changing document ownership. The README is for human orientation; do
  not make humans depend on these agent instructions for technical understanding.
- For an authorized implementation change, update its authoritative documentation
  with the new contract, following the shared guideline sequence. Before closing
  the change, verify code and documentation agree. Planned text is not an as-built
  claim until its implementation exists.
- A prototype shortcut is acceptable. Identify its exact scope and missing behavior;
  do not imply concurrency, recovery or safety guarantees that have not been built.
- Record which checks actually ran. Existing tests or source inspection are not a
  fresh passing suite, and finite checks do not establish untested guarantees.
- Validate local Markdown links, section references and whitespace. Cross-repository
  links are orientation links and depend on the documented sibling-checkout layout.

## Pre-1.0 development

- Repositories and development state are ephemeral until `v1.0.0`.
- Do not add version bumps, migrations or backward-compatibility mechanisms merely
  to accommodate a design-spiral iteration.
- This does not authorize deleting unrelated data, external resources or historical
  evidence. It does not weaken immutable-record semantics inside a repository.
- Prefer minimal implementations and more iterations; go broad or deep according
  to the concrete learning goal. Do not expand scope to finalize the whole design.

## Initial evidence

The initial technical documents were checked against code at `638cc42`, including
`src/record.c`, `src/object_id.c`, `src/repo.c`, public headers and their tests.
This records inspection provenance, not a pin preventing future authorized changes.
