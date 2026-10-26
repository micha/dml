# Independent Stage 0 corpus review

## Disposition

**Needs correction — limited to Stage 0 validation.** The frozen corpus's evidence
mapping is substantially truthful and reproducible. No consequential A–E factual
contradiction was found against the curated original evidence. However, focused
checks expose eight acceptances of malformed acquisition/validation inputs. Repair
these small fail-closed checks and rerun review before calling the package accepted.
This is not a demand for a UI, graph schema, new historical evidence, or later stages.

Reviewed manifest SHA256:
`e390d5606f01a4f365ceb4d3c604877f7cc451339a5b555a581ddd9c5f9fde00`.
The curator's manifest, report and summary hashes match its completion marker.
A completion marker does not imply acceptance.

## Commands and measured results

All commands ran from `/work/repos/micha/dml-design`, using existing Python
**3.13.15**, with no installs, network calls or feasibility-script execution.

| Command | Outcome |
| --- | --- |
| `mountpoint /work` | Exit 0; mounted |
| `python3 --version` | Exit 0; Python 3.13.15, reviewer environment only |
| `python3 -B observer-study/corpus/corpus.py` | Valid offline: 23 snapshots, 17 facts, five scenarios, nine gaps, ten historical bindings |
| `python3 -B observer-study/corpus/corpus.py --sources --availability` | Valid; all 23 originals reconstruct byte-identically; six explicit no-follow metadata observations: four regular files, two directories |
| `python3 -B observer-study/corpus/test_corpus.py` | Exit 0; **29 tests pass**, zero failures/errors, including isolated full refreeze |
| `python3 -B observer-study/review/focused_checks.py` | Exit **1**, intentionally: independent integrity succeeds; **16 reject-required probes, eight correct rejections, eight unexpected acceptances** |
| `python3 -B observer-study/corpus/corpus.py --sources --availability` (after focused probes) | Exit 0; same valid corpus and original hashes |
| `git diff --check -- observer-study/review` | Exit 0; untracked files need separate validation |

The review source is [focused_checks.py](focused_checks.py). It imports only the
corpus checker under review, **not historical producer modules**. Its independent
JSON decoding, selectors, SHA256 calculations, canonical byte reconstruction and
citation checks verified **23 originals / 183,588 original bytes**, **99 selected
rows**, **78 citation uses** (facts, gaps and availability), **ten historical digest
bindings**, and **69,976 fixture bytes**. Citation uses are not distinct trials.
Only the bounded no-follow file reader is shared with the checker for this pass.
Strict independent parsing found no duplicate keys/nonfinite constants in the
actual 23 JSON/text originals where applicable.

Machine outputs: [offline](../runtime/stage0/reviewer-offline.json),
[validation](../runtime/stage0/reviewer-validation.json),
[29-test transcript](../runtime/stage0/reviewer-tests.txt),
[focused results](../runtime/stage0/reviewer-focused.json), and
[final validation](../runtime/stage0/reviewer-validation-final.json).
Focused probe temporary copies were created under reviewer-owned ignored runtime
and removed. A final artifact check validated all **six local report links**,
parsed the reviewer source syntax without execution, checked trailing whitespace,
and confirmed the original manifest hash remained unchanged; results are in
`observer-study/runtime/stage0/reviewer-artifact-validation.json`.
The documented curator tests use their existing ignored
`corpus/runtime/` temporary scratch and remove their cases; no frozen corpus files
were edited. Review source/report and all reviewer outputs are confined to the
assigned areas.

## Prioritized findings

These are validator defects, **not proof that the present snapshots were altered**.
Package mutations deliberately update the relevant unsigned manifest hash, just
as the curator's semantic tests do. No original feasibility bytes are modified.
A raw change without rehashing remains rejected. This review does not demand signed
manifests or resistance to coordinated replacement of the entire checker/package.

### R1 — Medium: offline format/provenance validation is not fail closed

**Locators:** `corpus/corpus.py:153–161,174,181–185,215–222`;
`reviewer-focused.json` probes `unknown-source-kind-offline`, `unknown-gap-schema`,
`contradictory-answer-ingestion`.

- Changing `allowlist.json /sources/2/kind` (`initial-code`) from `text` to
  `future-format` returns `status=valid` offline. Line 174 treats every non-JSON
  kind as text. Source checking rejects it later, so the two checking modes
  disagree on support for the package's declared format.
- Changing `gaps.json /schema` to `future-gap-v99` still returns valid.
- Changing `ground-truth.json /ingestion` to `live-native` still returns valid while
  the manifest remains retrospective.

**Impact:** unknown versions and contradictory machine-readable acquisition claims
can pass the default acceptance check, including when originals are unavailable.
The real frozen values are correct; this is not a current live/native claim.

**Correction:** explicitly validate the finite source-kind and gap-schema values,
and require answer ingestion to agree with retrospective manifest acquisition in
both modes. These are already defined Stage 0 fields, not new graph conventions.

### R2 — Medium: original JSON acquisition silently normalizes malformed evidence

**Locators:** `corpus/corpus.py:79–88` versus `110–113`;
`reviewer-focused.json` probes `duplicate-original-json-keys` and
`nonfinite-unselected-original-value`.

`load()` rejects duplicate/nonfinite JSON in package files, but `project()` uses
plain `json.loads(data)` on originals. Synthetic original `{"x":1,"x":2}` selected
at `/x` becomes `2` without rejection. `{"x":1,"other":NaN}` selected at `/x`
also succeeds because the invalid unselected field never reaches canonicalization.
This can conceal ambiguous/invalid original data during selection.

**Correction:** use a shared strict byte decoder for both original acquisition and
package loading, rejecting malformed originals before any projection. The present
allowlisted originals independently parse strictly; **no existing malformed source
or missing value is alleged**. These probes call only projection over synthetic
bytes, never a producer script or runtime original.

### R3 — Medium: scenario coverage can be asserted with an empty scenario

**Locators:** `corpus/corpus.py:184–185,203–214,234–235`;
`reviewer-focused.json` probe `empty-scenario-facts`.

Removing every A fact (`ground-truth.json /scenarios/0/facts=[]`) and rehashing that
file still yields `status=valid, scenarios=5, facts=13`. Coverage only checks labels
A–E, not that each scenario has any cited facts. The readable answer sheet remains
unchanged, so contradictory structured/readable coverage can go unnoticed.

**Correction:** require nonempty cited facts in each scenario. Optionally compare
readable-sheet generation with structured truth using the existing authorship
recipe; do not attempt general prose truth verification. Do not hardcode 17 facts
as a universal design rule. The current five scenarios are populated and their
current readable/structured answers agree.

### R4 — Low: byte lengths and unit types are recorded but not validated

**Locators:** `corpus/corpus.py:130–138,153–161,210–211`;
`reviewer-focused.json` probes `negative-original-byte-count-with-sources` and
`non-string-unit`.

An original byte count of `-1` passes even with source verification; a nonempty
list such as `["made-up-unit"]` passes as a fact unit. The checker verifies only
hashes for the former and truthiness for the latter.

**Correction:** validate basic field types/ranges; compare `original_bytes` with
actual source length when sources are checked. Do not infer scientific meaning
from arbitrary unit prose. Independent checks confirmed all **current** recorded
lengths and the reviewed facts use meaningful distinct string units.

## Evidence-mapping challenge: scenarios A–E

### A — Original flaw, sealing fix, new capture flaw: supported

- Original unsafe deletion: `feasibility/hardening-review/evidence.json
  /review/cases/saved_plan_swapped_after_final_check` explicitly reports the retained
  resource destroyed despite exclusion from the ticket. The *separate* replay's
  retained UUID is in `feasibility/gate/followup-test-results.json
  /baseline_replay/initial_plan_swap_destroys_retained_other`.
  `followup_tests.py:64–76` also asserts empty post-effect resources;
  `gate-initial.py:191–216` shows check followed by mutable-path apply.
- Correction: follow-up `/adversarial/sealed_plan_survives_actual_final_barrier_swap`
  records mask 15, four EPERM mutations, approved plan digest, surviving UUID and
  absent victim. Independent final audit `/cases/sealed_saved_plan_swap` records
  descriptor argv/pass_fds, mask 15, preserved retained identity and victim deletion.
  The imported initial/current gate hashes differ and match the respective reported
  historical/current manifests. Current gate is not substituted for v1.
- New flaw: final audit `/cases/uncaptured_tofu_json`, `audit.py:132–145`, and
  `gate.py:62–76` corroborate same-census untracked literals and an unchanged material
  digest. State retains the planned untracked literal, not the later edited literal.
  **Input capture fails; memfd sealing does not.** No extra retained deletion is
  demonstrated by this case.

No final-audit numeric victim/survivor UUID is supplied. Borrowing follow-up UUIDs
would invent provenance; the corpus correctly refuses that. Raw plans/state remain
uninspected, so preservation/deletion is reported evidence, not new reproduction.

### B — Ordinary import/overwrite versus actual artifact adoption: supported, bounded

`feasibility/opentofu/evidence.json /probes/local_adoption` retains actual import
error, create action and safe synthetic before/after strings
`execution-created-content` → `configuration-content`. `/probes/surrogate_import`
is explicitly state-only `terraform_data`, not external-artifact preservation.

`feasibility/artifact/test-results.json /checks` reports actual custom-provider CLI
and declarative import, identity/content preservation, lost-state reimport and
SIGKILL recovery. `/counterexamples` retains forced replacement deleting before
Create failure. Final audit `/cases/same_file_sealed_provider_journal_bridge` is a
separate reported preservation/disposal check, not the surrogate.

**Gap accepted as explicit:** numeric before/after digest/inode/mtime pairs are
absent from permitted results. A boolean preservation assertion is not a receipt
or an inspectable numerical comparison. The answer sheet states that limitation.
A separately authorized safe receipt export could strengthen later inspection,
but raw state inspection is neither needed nor authorized to correct R1–R4.

### C — Unknown versus failure; cleanup versus computation: supported, separated

Initial gate `/cases/interrupted_apply` records exit 73 and no side effect start;
`/cases/completed_effect_unknown_outcome` records unknown after an effect, empty
manifest and no automatic acknowledgement. An exit code alone is not the durable
outcome. Hardening review `/review/cases/integrated_SIGKILL_after_provider_effect`
records `-9`, file absence, durable intent and stale manager state; later
`/integrated_recovery_and_historical_association` records acknowledgement/absence.

Archived journal-v1 `/latest/crashes` retains creation-before-registration orphan
count 1 and `recovered=false`. v2 `/latest/baseline_crashes` reports count 0 and
recovery; `/latest/followup_observations` retains same-byte replacement ambiguity.
The v1 code digest is checked against v1 evidence, not v2.

Only history `/scenarios/5–7` supplies simulated request/attempt progress, unknown
outcome, working/working/done, computation success and failed cleanup/remediation.
**No real end-to-end research computation timeline is available.** The corpus
correctly does not splice that simulation into the physical disposal sequence or
count the final audit as another SIGKILL reproduction.

### D — Reuse versus identical fresh work: supported with a source-derived gap

History `/scenarios/1` records distinct requests/attempts with one result root;
`/scenarios/2` records two modeled trials versus one naive content record.
`run_scenarios.py:28–73` constructs the two fresh calls. They are simulated
executions, not physical or Stage 0 trials.

The two-request/one-attempt reuse example comes from `test_model.py:90–109`, not
an emitted occurrence trace. `/scenarios/3` records selection behavior only;
`history/summary.json /tests` reports 24 tests, not another execution of this
individual trace. The corpus correctly labels the exact count **source-derived**.
`/scenarios/10` separately distinguishes one attempt from two hidden simulated
executions. Full occurrence IDs/accounting cannot be recovered from these summaries.
No IDs were fabricated and ingestion adds no independent empirical observation.

### E — AWS source-only and availability: truthful, incomplete by design

`adversarial/summary.json /evidence/cloud_executed=false`, the pinned manifest and
`source-notes.md:52–94` support **reported source inspection**, not cloud outcomes.
The notes constrain all-version deletion to exact matching key and warn that
unchanged import can no-op; neither every import nor prefix-wide deletion is
claimed. Runtime primary-source copies were **not read or rehashed** here.
Their lstat presence does not authenticate the authored source trace.

The six explicit support-path lstat observations remain separate from historical
execution events and copied fixture hashes. All six are currently present. No real
missing/excised dataset was discovered or invented; external URLs remain unqueried.
Missing, restricted and disappeared originals are tested synthetically. History
`/scenarios/9` explicitly says simulated deletion assertion and no sensitive-content
erasure. This is sufficient for a truthful small Stage 0 corpus, **not a complete
real-world unavailable/excised example**.

## Passing safety and integrity checks

- Original and normalized identities remain distinct: full-file SHA256 versus
  canonical selected-value SHA256. Independent selectors verify actual JSON
  pointers and exact retained newline-preserving line spans, not locator strings
  alone. All 78 citation uses resolve and agree with their frozen origins.
- All ten archive/current digest bindings agree with the reported manifests;
  equality is not authentication, timing, independence or complete closure capture.
- Documented deterministic reconstruction and full refreeze pass. Full refreeze
  requires unchanged metadata availability; offline fixture checking does not.
- Unknown source/fact evidence classes, tampered bytes, broken citations,
  undeclared manifest members and fabricated historical-ID count are rejected.
- Path traversal, absolute paths, parent/leaf symlinks, hardlinks, FIFOs and
  oversized reads are covered by the passing documented checks; focused probes
  confirm supporting-path traversal and fixture-symlink rejection. Metadata checks
  do not dereference paths or load runtime content.
- Bounded selected evidence contains synthetic literals, source excerpts, reported
  UUIDs/hashes, local locators and authored notes. No credentials or actual sensitive
  payload were identified in inspected selections. This is a selection review,
  **not a universal secret-detection certification**. Imported scripts/commands and
  URLs were treated as data, never instructions to execute/fetch.
- Metrics stay separate: model tests, result groups, CLI invocations, requests,
  attempts, modeled executions and result roots are not a generic tests total.
  Passing counterexample probes remain unsafe tested-system outcomes.
- Duplicating a fixture or citing one source repeatedly adds no reproduction. The
  independently reported final-audit swap/bridge is distinguishable from its
  inspection of earlier kill evidence.
- No complete environmental closure or missing input was invented from code hashes.
  Privacy notes correctly warn that retained selected copies survive original
  deletion; no external retention, GC or global erasure assurance is claimed.

## Limits and next action

This is an independent-context review of retained structured evidence and selected
safe source, not authenticated historical replay, cross-model consensus or fresh
provider/kernel/cloud execution. No raw producer runtime files, state, receipts,
logs, source bundles, sessions or tools were loaded; only six explicitly cited
runtime paths received no-follow metadata observation. No feasibility or DML files,
root/design docs, corpus fixtures/checker or later-stage code were edited. No commits,
pushes, delegation, services or infrastructure actions occurred.

**Curator action:** correct R1–R4 in its owned area, keep frozen evidence identities
and explicit gaps truthful, and rerun both documented checks and
`python3 -B observer-study/review/focused_checks.py`. A successful focused rerun
should reject all 16 malformed cases without modifying the reviewer test.
Retain the B–E evidence limitations; do not silently manufacture receipts, IDs,
primary-source verification or availability history to improve appearance.
The coordinator/user decides whether these explicit corpus limitations are adequate
for any later assignment. **No later stage is authorized or started by this review.**
