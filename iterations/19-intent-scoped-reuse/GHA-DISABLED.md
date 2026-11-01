# Design-spiral development CI disabled

## User decision and applied state

The user said: “let's just disable gha for the design spiral, i don't se any value in it”.
The coordinator scoped this to development CI, leaving release automation untouched.

Applied and verified on 2026-11-01 at approximately 19:09 UTC:

- Repository: `micha/dml`.
- Workflow `CI`, ID `232868302`, path `.github/workflows/ci.yml`:
  **`disabled_manually`**, confirmed by GitHub's workflow API and workflow list.
- Workflow `Release Python`, ID `233518745`: **`active`**, independently confirmed.
- Command: `gh -R micha/dml workflow disable 232868302`, exit 0.
- No workflow-file edits, source changes, builds, tests, commit or push were needed.
  Implementation HEAD remains `47131da927d76b190bb37f4384d887f2edcb65f5`, clean.

This is GitHub's workflow-level disabled state, not a repository-wide Actions shutdown
or conversion to manual dispatch. Do not enable or launch development GHA for the design
spiral without a new user decision. Local validation tests/thresholds and release controls
are unchanged. Historical handoff requirements and the implementation validation policy's
automatic final-SHA CI wording are superseded prospectively by this user decision only;
old outcomes are not rewritten. No production fix or further implementation is authorized.

## Investigation disposition

The existing window-2 worker explicitly acknowledged **PAUSED ALL activity**, no further
tools, after the coordinator relayed the decision. Both shared builds and maintained source
remain coordinator-owned. Frozen original/candidate/evidence are retained. Private harness
source under `build/iteration19/investigation/native-fix-source/harness/` is **incomplete and
unexecuted**; it is not an accepted or tested production fix. Reserved fix CI will not launch.
No compiler/native actors/builds/production edits/package operations or publication occurred
in this private preparation phase. Intermittent provider errors and unfinished work remain
part of the record, not a native test failure.

## Preserved outcomes and limitations

Latest three development CI runs are completed, so disabling needed no cancellation:

- `41269736666`, feature SHA `a71e89f`: raw **failure**.
- `41294882995`, diagnostic SHA `beafc0ee`: raw **cancelled**.
- `41299279030`, diagnostic SHA `47131da`: raw **cancelled**, even though complete
  test reports passed; macOS x86 exceeded the outer 20-minute cap.

Actual-platform named-resource lifecycle controls establish a mechanism, not exact attribution
of historical asynchronous-story failures or VP-001. Those causes and macOS x86 slowdown remain
UNKNOWN. Disabling GHA is not a pass, diagnosis, native fix, release-assurance claim or automatic
final Iteration19 disposition. Feature acceptance/publication and unresolved investigation
remain distinguishable. See [investigation](CI-INVESTIGATION.md) and [review](REVIEW.md).

## Reversal

Only if separately requested: `gh -R micha/dml workflow enable 232868302`, followed by API
verification of `active`. Re-enabling does not itself authorize reruns or native investigation.
No design-repository commit/push was requested.
