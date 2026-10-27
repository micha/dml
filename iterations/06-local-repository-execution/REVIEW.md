# Iteration 6 coordinator review

Status: bounded implementation, independent review, focused worker publication and
final exact-SHA CI verification are complete. Turn accepted and stopped.
[RESULTS.md](RESULTS.md) owns worker
evidence; [COORDINATION.md](COORDINATION.md) owns assignment/build gates.

## Source inspection and feedback

Reviewed the 16-file implementation slice over `0ec769b`: public-API-only explicit
`daggerml.exchange`, install seam, maintained A → B → A example, selection/framing,
typed-role/history, process/file/storage tests and owning as-built contract.
Native production, original local/transfer implementations/contracts, old spec,
CLI grammar/JSON, adapter, runtime/version and workflows are unchanged.

Preparation reads explicit C and selected tree entries, closes handles and exports
without A writes. Execute acquires a retained exclusive marker before initializing
B/import/dispatch, calls unchanged public `run_step`, exports exact F and publishes
receipt last. Requests/attempts originate in B. Receive compares caller-owned expected
selection/token, validates complete output and selected roles/history in disposable
storage, prepares owned outcome data and closes/cleans scratch before atomic public
A import. It neither updates main nor adopts/replaces history, recreates mutable
B refs, runs captured source or acts on historical paths. Recorded computation failure
and cleanup remain separate; missing history stays unknown.

Early feedback strengthened successful genuinely-new actual-A put instrumentation
before real map-full and substituted consuming-commit errors; raw different/malformed
ref preservation; separate-worker completion/reaping before caller interruption;
actual recorded failure relabelled as success; and generated history/repeat-receive
properties. Worker added regressions without production changes. Read the final
fixtures and evidence, including safe process barriers around actual A commit.
No functional production defect or outstanding within-scope finding was found.

Selected refinements remain qualified: `map_size` controls B bootstrap/input import
or final A import, not local-run/result quota; unchanged runner reopens B using its
existing defaults. Duplicate validation import is a deliberate prototype cost.
Structural consistent records/token echo are not worker authentication or independent
proof of external truth. No full environment capture, sandbox, automatic retry,
recovery, process-tree cleanup, power-loss durability or exactly-once promise.

## Independent installed probes

Separate pip-less `/tmp/dml-iteration6-review-install.*` venv was populated offline
through existing project-local packaging tools from current worker-built core/console
wheels. No shared build directory/global tooling touched. Session-local
`/tmp/dml-iteration6-coordinator-probe.py` executes outside checkout with PYTHONPATH
unset and passes **73 independent checks**, exit **0**;
`/tmp/dml-iteration6-coordinator-install.{log,exit}`.

- Installed module/extension provenance; fresh worker subprocess with A renamed away.
- Two fresh workspaces/Bs: distinct request/attempt occurrences, equal result 11.
- Independent public breadth-first typed population/every packed byte, including
  composite-only descendants; source/input/B/returned closure equality and ordered
  pre/publication/final parents.
- Fresh receiver subprocess with B offline, packet-only files and caller-owned expected
  selection separately supplied; main independently moved after pin stays moved.
- Saved source/sentinel records and refs preserved; B working/reservation/publication
  refs absent. Repeated receive is equal and starts no new execution; repeat execute
  rejects with unchanged A state.
- Existing installed console log JSON agrees with returned commit/history.
- Real nonzero child after accepted publication returns recorded failure with result
  retained only as evidence, separate cleanup and unchanged A heads.
- Swapped otherwise-identical job packet and valid wrong-intent completion (token
  edited to expected) reject before A writes, with entire data-file equality.

Wheel `__init__`, exchange, local and transfer Python bytes equal maintained reviewed
sources. Evidence is local CPython **3.13.15 / Linux x86_64**, `cp313-abi3` core and
pure console wheel, not earlier declared Python, other platforms, sdist/release,
coverage-instrumented installed children or access-control/security assurance.
Worker's separate installed 252-check harness and actual child provenance assertions
are worker evidence, not a coordinator rerun.

## Independent default validation and acceptance

After worker explicitly froze runtime/tests/as-built edits/build use and released
both `build/check` and `build/coverage`, coordinator ran from `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh run exits **0**; `/tmp/dml-iteration6-coordinator-check.{log,exit}`:

- **609 Python tests**, **seven C executables** pass.
- Python **1,639/1,639 statements**, exchange **344/344**, example **132/132**.
- Retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
- Binding Valgrind: **zero unsuppressed errors**; existing CPython runtime patterns
  suppress 624 contexts, retained heap 500,823 bytes/8,717 blocks (476,387 bytes/
  8,657 blocks suppressed; 24,436 bytes/60 blocks reachable).
- **141 native CLI Valgrind processes** pass. No new exclusion/suppression/weaker gate.

Host-helper statement coverage is not every Python branch or installed-child coverage.
Old native precise exclusions, unsupported foreign-last-owner abandonment, unavailable
Python mutation frameworks and five selected worker negative oracles remain qualified;
Mull is not Python mutation evidence. Private substituted commit errors are not real
disk-device faults. Finite local cooperative process loss is not general descendant
cleanup/security or power-loss assurance.

Coordinator validates **16 Markdown documents / 323 local targets/anchors** and
whitespace in both repositories. Implementation index remains empty; no unrelated
implementation work was found. Design changes stay separate and uncommitted.

This bounded implementation is satisfactory. Coordinator releases both shared build
directories back to worker and authorizes inspecting/staging only the reviewed 16-file
implementation slice, focused commit and normal push to existing branch/remote, then
automatic exact-SHA CI monitoring and bounded reviewed fixes. No force push, new remote,
release/tag/package publication, extra workers, cloud experiments or later feature turn.
Final publication/CI evidence follows. No later feature turn is authorized.

## Final publication and exact-SHA CI

Worker inspected/staged the reviewed **16-file** slice (**2,830 insertions/4 deletions**)
and normally pushed
[`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`](https://github.com/micha/dml/commit/a0aa05d56b9e70277a98bb03e26514ab6b6f1415)
(`Execute pinned steps across independent local repositories`). Coordinator independently
verified the committed surface, clean implementation tree/index and exact remote master.
No design notes were staged/committed.

[CI run 40593738345](https://github.com/micha/dml/actions/runs/40593738345) succeeds
for that exact SHA on the **first run**, all **six jobs** successful. No CI follow-up
fix/rerun was needed. Coordinator fetched complete job/run JSON and full logs, checked
the sole exact-SHA automatic push workflow list and independently ran finite
`gh run watch --exit-status`, exit **0**. Existing finite job bounds and Windows
verbose diagnostics remain unchanged.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244182) | Success | 7 | 609 passed; 23.92 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40593738345/job/122504243877) | Success | 7 | 609 passed; 31.02 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244150) | Success | 7 | 605 passed, 4 existing skips; 121.60 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244001) | Success | 7 | 605 passed, 4 existing skips; 60.27 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40593738345/job/122504243964) | Success | 7 | 604 passed, 5 existing skips; 71.60 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40593738345/job/122504243605) | Success | 7 | 609 passed; 48.36 s |

Existing skips concern absent `/dev/full` and Windows' Unix pipe case. No new skip,
source exclusion, weaker gate, reduced boundary input or workflow change. Strict CI
is informational **`-c`**, not independent local default/memory **`-v`**; its Python
1,639/1,639 and retained native totals do not establish installed-child coverage.
All earlier trust/profile/platform/mutation/cleanup qualifications remain.

Session-local evidence: `/tmp/dml-iteration6-coordinator-{ci.json,ci.log,runs.json}`
and `/tmp/dml-iteration6-coordinator-watch.{log,exit}`. Current GitHub CLI verification
syntax was consulted through Context7 `/websites/cli_github_manual`.
Coordinator instructed worker to finalize only RESULTS and stop all implementation/
build/staging/commit/push work. No force push, manual workflow, tag/release/package
publication, extra workers, cloud/global tooling or later feature turn.
These delivery/review notes are included in the user's subsequent local design
checkpoint alongside Iteration 7 candidate planning. Earlier uncommitted/no-checkpoint
statements describe completion-time provenance; no design push is requested.
