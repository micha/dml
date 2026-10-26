# Observer study

## Current assignment

Stage 0 of the [handoff](HANDOFF.md): curate a small truthful evidence corpus for
human inspection. Execution was authorized by the user after the planning handoff.
Graph conventions, model-reader implementation, UI technology and later stages
are not selected or authorized by this assignment.

The question is whether a deterministic independent observer can make unfamiliar
research understandable through uniform navigation and inspectable evidence.
This milestone prepares the evidence, not the observer itself.

## Ownership and delivery

- `corpus/`: curator-owned allowlisted fixtures, original hashes, source locators,
  provenance, answer sheet, evidence gaps, integrity checks and tests.
- `review/`: independent review of the finished corpus and its evidence mapping.
- This index and final status: coordinator-owned scope and synthesis.
- `runtime/`: ignored task briefs, frozen launchers, worker summaries, completion
  markers and process-exit records. These are not historical research executions.

Workers run interactive Pi in workmux-created windows in the existing tmux
session. They load `workmux-notify`; prompts and steering are sent through
`tmux send-keys`. Notifications indicate that a turn stopped, not that acceptance
criteria passed. Finished reports precede atomic completion markers; process
outcomes are checked separately.

## Evidence boundary

The producer is the existing [feasibility study](../feasibility/README.md).
Ingestion is retrospective. Original failures and before/after versions remain
intact. Source inspection, simulation, recorded effects and authored claims must
remain distinct. Reuse is not another independent trial, and metrics retain their
original units. Missing evidence and uncaptured history stay explicit.

The implementation repository `/work/repos/micha/dml` remains read-only. No
feasibility reruns, raw session/state/log sweeps, cloud experiments, new tool
installations, OS changes, commits or pushes are part of this assignment.
Generated artifacts stay ignored. Importing evidence never executes it.

## Status

Stage 0 is **complete with a qualified independent pass**. See [RESULTS.md](RESULTS.md)
for measured checks, preserved review/correction history, evidence gaps and the
next decision. Start human review with the [corpus answer sheet](corpus/ANSWER-SHEET.md).

All 39 local corpus tests passed; all 16 independent malformed-input probes reject
correctly after correction. These are validation counts, not historical research
trials. Existing producer files and the DML implementation remained unchanged.

Both interactive workers exited normally and their two owned windows were closed.
No graph reader or UI has been implemented. Work is paused for user review before
Stage 1, graph conventions or presentation technology are selected.
