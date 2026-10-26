# Agent guide

## Scope

This repository contains user-led exploratory DML design work. Read `README.md`
and `discussion.md` before continuing the discussion. Read the shared
[glossary](../dml/docs/spec-next/glossary.md) for the vocabulary.

- Keep conceptual agreements, tentative directions, assistant suggestions, and
  open questions distinguishable.
- Design discussion is not approval to implement or amend DML specifications.
- The user authorized isolated feasibility prototypes, local sandbox experiments
  and candidate-design evolution under `feasibility/`. Read its index,
  `ITERATION-RESULTS.md` and final audit for completed work and limitations. This
  does not authorize cloud experiments or production integration.
- Keep the implementation repository `/work/repos/micha/dml` unchanged unless
  separately authorized.
- Preserve corrections and uncertainty rather than silently turning proposals
  into decisions.
- Files under `archive/` are historical context, not active instructions. Do not
  execute their old coordinator or completion-marker protocols.

## Vocabulary

- Maintained documentation uses glossary terms consistently. Add or clarify a term
  when needed; do not silently give an existing term a different meaning.
- Design conversation follows the glossary on a best-effort basis. Informal phrasing
  is acceptable; clarify ambiguities that affect design and record agreed corrections.
- Keep provisional definitions provisional. Glossary inclusion does not imply an
  implemented feature or select a schema/API.
- Exact code identifiers, quotations, archived reports and frozen evidence may retain
  their original vocabulary. Explain mappings where useful; do not rewrite history.

## Notes and commits

- Maintain design notes here, not under the retired temporary task directory.
- Keep `discussion.md`'s resume point current when recording a checkpoint.
- Use small, focused changes and validate local Markdown links.
- Never commit credentials, secret values, or sensitive research data.
- Make checkpoint commits when requested. Do not create a remote or push unless
  authorized.
