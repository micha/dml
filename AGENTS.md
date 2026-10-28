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
- Keep the implementation repository `/work/repos/micha/dml` unchanged outside
  separately authorized scope. The user has authorized code changes there for
  [Iteration 1](iterations/01-minimum-viable-repository/HANDOFF.md): the minimum viable
  repository, plus the already authorized `docs/spec-next/` documentation. This
  does not authorize later execution/resource/observer work. The user also
  authorized [Iteration 2](iterations/02-repository-usability/HANDOFF.md): the
  low-level Python repository API and inspection-only CLI, including bounded local
  build/install validation and review fixes. No later feature turn is authorized.
  The user also authorized [Iteration 3](iterations/03-composable-dags/HANDOFF.md):
  composable named DAGs and scoped lookup, implementation by the existing Pi agent
  in window 2, coordinator monitoring/review and fixes, then focused commit/push
  after acceptance and exact-SHA CI verification/fixes. This does not authorize
  a release, package publication, additional workers or a later feature turn.
  The user also authorized [Iteration 4](iterations/04-local-recorded-execution/HANDOFF.md):
  one locally executed, recorded Python step by the existing window-2 Pi agent in
  a new session, coordinator monitoring/review and fixes, then focused commit/push
  after acceptance and exact-SHA CI verification/fixes. No extra workers, release,
  package publication, cloud experiments or later feature turn are authorized.
- Iteration 5 [plan and handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md)
  are approved for pinned snapshot transfer between local repositories. The user
  authorized implementation by the existing window-2 agent in a new session,
  coordinator monitoring/review and fixes, then focused worker commit/push after
  acceptance and exact-SHA CI verification/fixes. No extra workers, release,
  package publication, cloud experiments or later feature turn are authorized.
- Iteration 6's [plan and handoff](iterations/06-local-repository-execution/HANDOFF.md)
  are approved for synchronous execution across local repositories, with the
  unchanged-caller-head/explicit-return-ref boundary. The user authorized implementation
  by the existing window-2 Pi agent in a new session, coordinator monitoring/review
  and fixes until satisfactory, then focused worker commit/push and exact-SHA CI
  verification/fixes. This bounded turn is now complete and stopped at published
  `a0aa05d`, all six exact-SHA CI jobs successful; see
  [review](iterations/06-local-repository-execution/REVIEW.md). This is not permission
  to restart implementation or begin another turn. No extra workers, release/package
  publication, cloud experiments or later feature turn are authorized.
- Iteration 7's [plan and handoff](iterations/07-asynchronous-local-execution/HANDOFF.md)
  are approved for asynchronous same-machine execution and inspectable progress through
  bounded adapter invocations, with separate saved observation handle/live application
  process ownership. The user declared GO and authorized implementation by the existing
  window-2 agent in a new session, coordinator monitoring/independent review and fixes
  until satisfactory, then focused worker commit/push and exact-SHA CI verification/fixes.
  This bounded turn is complete and stopped at published `a8d6463`, all six exact-SHA
  CI jobs successful; see [review](iterations/07-asynchronous-local-execution/REVIEW.md).
  This is not permission to restart implementation or begin another turn. No extra
  workers, release/package publication, cloud experiments, detached supervision service
  or later feature turn are authorized.
  See [coordination](iterations/07-asynchronous-local-execution/COORDINATION.md).
- Iteration 8's [plan and handoff](iterations/08-caller-recorded-requests/HANDOFF.md)
  are approved: A explicitly records Q before launch; B registers imported Q locally
  and creates only T, reusing asynchronous observation/explicit-ref return. The public
  seams, atomic two-ref A publication and pinned-Q validation are the bounded plan;
  illustrative spellings remain refinable. The user requested a local design checkpoint,
  not implementation, delegation, worker restart, experiment, implementation commit/push
  or CI authorization. Do not inherit Iteration 7's completed GO.
- Preserve corrections and uncertainty rather than silently turning proposals
  into decisions.
- The user permits narrow coverage exclusions when exercising the precise
  lines/branches/regions adds no useful assurance. Preserve thresholds for the
  remaining code, document each rationale and distinguish tested from excluded
  code. Difficult but meaningful failure paths still need tests. See the
  implementation [testing guidance](../dml/AGENTS.md#testing).
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
