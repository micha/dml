# Stage 0 curator report

## Disposition

**Finished with gaps; not acceptance success or approval for Stage 1.** A deliberately
small retrospective evidence corpus now supports inspection of five scenarios with
explicit distinctions between reported effects, simulation, source inspection and
authored claims. No graph convention or presentation technology was selected.
Independent review found the A–E mappings substantially truthful but required
bounded validator corrections R1–R4. Those are now corrected and regression-tested;
acceptance remains a coordinator/reviewer decision, not a claim made here.
The original review findings and frozen evidence remain unchanged.

Review entrypoints: [README.md](README.md), [ANSWER-SHEET.md](ANSWER-SHEET.md),
[ground-truth.json](ground-truth.json), [gaps.json](gaps.json),
[allowlist.json](allowlist.json), [manifest.json](manifest.json),
[corpus.py](corpus.py), [freeze.py](freeze.py), and [test_corpus.py](test_corpus.py).

## Work and boundaries

Read the machine index and required administration instructions; confirmed `/work`
was mounted before using work-disk data. Read the repository guide, discussion,
handoff, iteration results and final audit. No additional nested repository
instructions were found. Documentation follows the applicable root guide: focused
owned changes, explicit status/uncertainty, and local Markdown-link validation.
No DML documentation was modified.

All writes were confined to the assigned corpus and `curator-*` completion artifacts.
Existing root/feasibility changes were left uncommitted and preserved. Only explicit
curated JSON/source files were read. Six reported runtime support paths received
bounded no-follow metadata checks; their contents were not loaded. No raw sessions,
provider state, SQLite databases, logs, binaries, runtime source bundles or arbitrary
external resources were opened. No network/tool installation, study rerun, native
DML write, cloud operation, delegation, commit, push or service change occurred.

The entrypoint scripts never import feasibility modules. Python standard-library
JSON, hashlib, no-follow filesystem reads and unittest suffice. Today's Python was
checked as **3.13.15**, only as curator environment metadata. Historical tool/kernel
versions and executable digests remain **reported evidence**, not curator-verified
tool installation or complete environmental capture.

## Acquisition and integrity

1. Froze **23 explicit original files**, each with full original SHA256 and byte
   length. Copied only reviewed JSON pointers and selected safe text line spans.
2. Stored selected values with exact original locators and canonical-value digests
   in **23 fixture envelopes, 69,976 bytes total**. This is selection/sanitization,
   not automatic sensitivity detection or a production record schema.
3. Authored **17 answer facts across A–E**. Every fact has citations, evidence class,
   explicit unit, harness result, tested-system outcome and limitations. Curator
   interpretation is explicitly separate from cited proof/claims.
4. Added **nine cited evidence-gap items** and **six metadata-only support-path
   observations**. All six paths were present (four regular files, two directories).
   Presence establishes neither hash agreement nor historical availability.
5. Verified **ten historical checksum bindings**: archived vulnerable gate against
   initial and review manifests; archived initial results against the initial
   manifest; journal-v1 archive against v1 evidence; current gate/helper/follow-up
   runner and final audit runner against reported follow-up/audit hashes. Current
   source was never silently substituted for v1.
6. Checked package/file hashes, selection digests, citation locators, classes,
   units, allowed paths and explicit occurrence boundaries offline; verified original
   hashes and byte-for-byte reconstruction separately.

The frozen original-file hash establishes what was read at curation. Equality to a
historical reported digest verifies those **bytes against that reported digest**;
it is not a signature, authenticated execution attestation, timestamp, proof of
independence or complete capture. Default checking works if original runtime
material disappears. `--sources` requires the frozen originals and fails rather
than refreshing them. Full initial refreeze reproducibility is tested in a separate
owned directory; frozen availability must be identical for full-package equality.
The ordinary checker reconstructs fixtures in memory without reobserving runtime
availability or writing sources.

## Scenario results

| Scenario | Exposed evidence | Unresolved boundary |
| --- | --- | --- |
| A | Original reviewed plan-path substitution; separate historical replay UUID; sealed follow-up mask/EPERM/survivor; independent descriptor apply; `.tofu.json` literals/source and recorded outcome | No raw plans/state; final audit numeric victim/survivor UUIDs absent. Separate runs are not merged. Capture bypass is not seal failure. |
| B | Unsupported ordinary `local_file` import and synthetic before/after overwrite; explicitly state-only `terraform_data` surrogate; actual custom-provider and bridge preservation assertions | No numeric adoption digest/inode/mtime before/after pairs in allowed results. Actual-provider checks are reported assertions. Forced replacement still deletes before failed Create. |
| C | Real process exit with durable unknown; joined SIGKILL-after-unlink, stale manager state and later acknowledgement; preserved v1/v2 creation gap | Real disposal recovery is not a recorded research computation. Request/attempt/computation/cleanup progress is only supplied by simulation; no stream splicing. |
| D | Two distinct simulated requests/attempts with one result root; reuse selection; source-derived two-request/one-attempt example; hidden-retry counterexample | Exact reuse count and request IDs absent from structured output. Source/test summary is not an individual retained trace or fresh physical experiment. |
| E | Pinned S3 digest/URL manifest and authored source trace, `cloud_executed=false`; separate Stage 0 support availability; simulated retirement/erasure limits | Primary S3 copies not rehashed/read. External URLs not fetched. No actual missing/excised dataset or global erasure demonstrated. |

Historical units remain distinct: the follow-up reports 28 regression groups,
22 adversarial groups, four replay groups and 285 CLI invocations; final audit
reports 55 plus 18 CLI calls; artifact suite reports 52 CLI invocations; history
summary reports 24 model tests. They are not summed into a tests-passed total.
Retrospective ingestion contributes **zero historical execution IDs** and no new
research observations/trials. Fixture source IDs and content hashes are not
request/attempt identities.

## Validation and commands

Commands were run from the design repository root:

```sh
python3 --version
python3 -B observer-study/corpus/freeze.py --initial
python3 -B observer-study/corpus/corpus.py
python3 -B observer-study/corpus/corpus.py --sources --availability
python3 -B observer-study/corpus/test_corpus.py
git diff --check -- observer-study/corpus
```

Measured initial validation: **29 tests passed**, no failures/errors. Both offline and
original-source checkers return `status=valid`: 23 snapshots, five scenarios,
17 facts, nine gaps and ten historical digest bindings. Original-source checking
reconstructs byte-identical fixture output. Full isolated refreeze reproduces the
allowlist, manifest, fixtures, ground truth, gaps and readable answer sheet.

Focused tests include tampered bytes; missing/restricted/changed originals; offline
survival of absent originals; missing fixtures; invalid citation pointers and
original/value digests even after rehashing; missing units and invalid evidence
classes; historical digest mismatch; occurrence/harness boundaries; traversal,
absolute paths, parent/leaf/fixture symlinks, hardlinks, FIFOs and oversized files;
metadata-only content-read exclusion; duplicate/nonfinite JSON; pointer escaping;
refreeze refusal; deterministic regeneration; and local Markdown links.

Two development issues were exposed, not concealed: the first initial-freeze
attempt rejected an out-of-range sealing-source line selector (76 versus actual
69) **before any frozen files were written**; correcting the explicit selector
allowed freeze. A pre-report validation run correctly failed the README's pending
`REPORT.md` link; creating this required report resolved it. No checks were weakened
and no study was rerun. Initial tests/checkers were run after report creation and
before the initial summary/atomic completion marker.

`git diff --check` is useful but does not cover untracked files; the focused tests
validate links in the new Markdown directly. No assertion of whole-repository
cleanliness or unrelated-source immutability is made. `--sources` validates the
23 allowlisted source hashes at completion, not every unrelated file on disk.

## Bounded R1–R4 correction and validation

The independent review recorded eight unexpected acceptances across 16 malformed
input probes. All five scenario mappings were substantially truthful; this was a
validator correction request, not authority to improve evidence by invention.
Its report, summary and `focused_checks.py` were not edited. Reviewer-script SHA256:
`083e98039e9f54abfd08929a7c0327ce922ef7d5f8d1368c1603217bffa663d2`.

Corrections in `corpus.py`:

| Finding | Correction | Regression coverage |
| --- | --- | --- |
| R1 | Validate source kind (`json`/`text`), gap schema (`stage0-gaps-v1`) and answer ingestion matching the retrospective manifest in both checking modes | Future kind/schema and contradictory ingestion rejected offline and with sources |
| R2 | Shared strict byte decoder for package and original JSON before selection; rejects duplicates and nonfinite constants/numeric overflow throughout the object | Selected duplicate and unselected nested duplicate; unselected NaN, Infinity, -Infinity and ±1e999; package decoder parity |
| R3 | Require nonempty fact list in every A–E scenario; existing per-fact checks require citations | Empty facts rejected for each of five scenarios in both modes; uncited fact rejected; no fixed global fact count |
| R4 | Require integer, non-boolean original length within 0–256 KiB and compare it with actual source length; require nonblank string units | Negative, boolean, fractional, string, list and oversized counts; plausible but wrong positive length; malformed/nonblank units in both modes |

Ten added regression methods bring the suite to **39 passing local tests**, no
failures/errors. The original source-tamper test now supplies same-length wrong
bytes so it continues testing the hash path separately from the new length check.
No existing rejection requirement was weakened.

Additional commands:

```sh
python3 -B observer-study/corpus/check_review.py
# After reports/tests and real completion publication:
python3 -B observer-study/review/focused_checks.py
```

The unchanged focused checker requires a marker to validate completion hashes.
To avoid publishing real completion before tests, [check_review.py](check_review.py)
first executes its identical bytes in a temporary corpus-owned mirror. It copies
only enumerated corpus files and the 23 bounded allowlisted source files, and
supplies a **validation-input-only, not-completion** marker and summary there.
The mirror is removed afterward. It imports no producer module, loads no original
runtime evidence, changes no reviewed script and creates no real current marker.

Measured pre-publication focused result: **16 required rejections, 16 correct
rejections, zero unexpected acceptances, exit 0**. Independent reconstruction
remains 23 originals / 183,588 original bytes, 99 selected rows, 78 citation uses,
ten historical bindings and 69,976 fixture bytes. These are validation units,
not fresh research trials. The normal unchanged live command was also run against
the actual report/summary/marker: **exit 0, 16 correct rejections, zero unexpected
acceptances**, with all three completion hashes verified. The marker was then
removed during final report/summary reconciliation and atomically republished after
final validation. Its own short-lived reviewer-probe scratch is an authorized
consequence of running that unchanged command; no `review/` files or original
reviewer outputs were modified.
Curator outputs use only `runtime/stage0/curator-*`.

Offline and source/availability checks pass after corrections. The frozen manifest
remains SHA256 `e390d5606f01a4f365ceb4d3c604877f7cc451339a5b555a581ddd9c5f9fde00`;
all manifest-listed fixtures, ground truth, readable sheet and gaps remain identical.
The allowlist is also unchanged. No new source, historical ID, receipt, timing,
availability event or substantive evidence claim was introduced.

The old current completion marker was removed before edits. Coordinator-backed
initial marker/summary and original review findings remain historical context.
The revised summary records the correction disposition and measured checks; a new
marker is atomically published only after documentation and pre-publication tests
finish. **Stage 0 only; original evidence gaps remain unresolved.**

## Limitations and questions for review

- Is reported provider preservation evidence adequate, or must a separately scoped,
  sensitivity-reviewed export of numeric identity/digest pairs be commissioned?
- Is the source-derived reuse count acceptable for Stage 0, or should the producer
  supply a separately reviewed retained occurrence trace? Do not manufacture IDs.
- Should later work obtain a safe pinned primary-source bundle to independently
  inspect S3 claims? This assignment did not authorize raw runtime reads/fetches.
- Is the missing real computation/request timeline acceptable, provided simulation
  and actual disposal are visibly separate? This corpus cannot reconstruct it.
- No actual excised payload or inaccessible external dataset is represented; tests
  cover synthetic missing/unavailable paths, not fabricated historical events.
- Checks validate integrity/structure, not truth of authored prose, authenticity,
  scientific independence, provider authority, universal confidentiality or safety.
- Copies persist independently of original excision. No GC root registration,
  durable external-resource retention promise or distributed erasure is implemented.

Completion artifacts are the compact `curator-summary.json` and atomically renamed
`curator-done.json` under the assigned Stage 0 runtime directory. The marker denotes
finished work with gaps, not review acceptance. **Stop here; later stages require
separate steering/authorization.**
