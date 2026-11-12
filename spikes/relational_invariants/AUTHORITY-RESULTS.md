# Selection authority: broader existing-test comparison

Status: bounded continuation complete, UNCOMMITTED in the isolated spike worktree.
No production/native/API changes, removed tests, push/CI, full suite or real-child/retired
fixture replay. Same pinned optional DuckDB1.5.2 binding and HOST fixture seam as the
[earlier12-case slice](PAIRED-TESTS-RESULTS.md).

## Additional existing assertions exercised

[test_selection_pairing.py](test_selection_pairing.py) directly invokes unchanged existing
`test_reuse_selection_records.py` assertion bodies with HOST-only fixtures:

| Family | Instances |
| --- | ---: |
| S/V fields, roots, roles, native node/datum types, completion ID size, header size | 15 |
| Partial graft of another successful producer's T/R/Q/F or expected/job/observation | 7 |
| Valid native S intent/binding/input claims swapped against public authority | 3 |
| Stored receipt token/commit/F/pre-dispatch/Q/T/phase swaps | 7 |
| **New instances** | **32** |

Previous12 cases are also rechecked. OS launches/network connects remain blocked. Fixed
captured test sources execute in-process; observations are HOST-authored, not child,
interpreter/deadline/custody proof. Original existing source bytes/assertions remain exact
at the worktree base. No maintained test-function or fixture file is changed.

## Independent authority rules added

[selection_checks.sql](selection_checks.sql) evaluates each requested commit/slot, rather
than assuming every intentionally bad test DAG in the store should be valid. It checks:

- Exact S fields/role/result root, scalar types, link kinds and target DAG availability.
- Completion bytes encode16-byte IDs, V fields/expected root, BYTES header types/8192 cap.
- Parsed handle/job/observation shapes/formats and expected-job/job agreement.
- Header token/commit/phase/F claims agree, and stored S/Q/T/success/result claims agree
  with native completion tree and actual occurrence owners.
- Job Q/binding/input/intent and receipt Q/T/pre-dispatch agree with native authority;
  selected F remains in pinned all-parent ancestry.
- Exact requested binding/full-input/intent matching for old exact-binding helpers.

[capsules.py](capsules.py) independently projects stored BYTES fields to UTF8/JSON. It does
not invoke DML semantic validators/private codecs. Missing/wrong-type/oversized/malformed
headers are retained as explicit error rows, not dropped. Nine pure projector controls
cover UTF8/JSON errors, duplicate-key rejection, nonfinite JSON, wrong containers,
wrong native kinds and exact8192-byte boundary. These are not native scenario tests.

Candidate packet checking now also sees the actual job, independently copied expected
public dimensions, receipt, and supplied snapshot-bundle root/fingerprint. Baseline
verdicts remain separate from all SQL predicate inputs.

These are selected claims/shape rules, NOT full equivalence to public validation. Full
raw bundle row/record/hash/order/framing/byte budgets, exhaustive descriptor type/name/URI
rules, every publication-parent/tree/cleanup/diagnostic condition, bounds, ref reservations
and real execution/custody still need direct or separately ported assurance. SHA256 here
identifies the supplied input bytes for scope deduplication; it is NOT independent validation
of every bundle record or scientific truth.

## Useful real oracle defect found and corrected

Initial `authority-v1` **RAWFAILED:43PASS/1FAIL,47.34s**. The existing original completion-swap
assertion passed, but our paired controller rejected contradictory verdicts for an apparently
identical candidate scope. This was a spike/oracle failure, not a DML runtime failure.

The bad selection changed its completion pointer to another successful F while retaining
the old V headers. Projection therefore exported a DIFFERENT snapshot bundle under the
SAME headers. The baseline distinguishes the bundle-root mismatch; our scope identity had
omitted the bundle. The same-scope guard exposed that omission instead of silently choosing
a passing verdict.

Correction: capture bundle root plus SHA256 as scope dimensions, retain observed events
before deduplication, and independently reject supplied-root/receipt disagreement. A
focused completion-swap regression then passes; the final broader run uses the corrected
source. No retry/timeout/skip/threshold weakening or production fix.

Original44-case failed gate/XML/log/data remain. `gap-root-evidence.json` on the SAME stopped
failed case confirms old receipt/bundle root and the different retained alternate packet
root. Transient projection bundle bytes and pre-dedup event objects were NOT retained in
that failed gate: retained packet roots/source flow support attribution, not a claim to have
those original transient bytes. New runs retain observed scopes early to improve provenance.

## Final results

`authority-final/tests.xml` and primary log: **55PASS,48.40s,true exit0**, zero failures/errors/
skips. This is44 original-body instances (prior12+new32), two prior harness guards and nine
new pure header-projector guards. No maintained full gate/coverage/platform result.

| Final44-case measure | Result |
| --- | ---: |
| Observed validator calls | 508 |
| Distinct scopes, including packet inputs where applicable | 218 |
| Rejected scopes independently reproduced | 65 |
| Acceptance/action disagreements | **0** |
| Per-repository unique normalized record reads | 8,154 |
| Setup+body public record reads | 1,165,746 |
| Distinct content IDs across collected case repositories | 4,280 |

All shared decoded-fact signatures agree and all native caller data hashes remain unchanged
by normalization. Reads include original production validation, worker/scratch stores and
unported assertions; scope/ID-set differences noted in the earlier report remain. These
are not all proven redundant obligations or removable test costs. Global proof pooling is
not implemented; physical repository availability is independently read per case.

Earlier97 scopes covered fewer selection-read obligations and less packet context. Current
218 is not a failure to deduplicate: it includes newly represented obligations and preserves
previously missing input distinctions. There is no universal object-ID-only validation key.

## Timing: broader assurance currently costs more

Single instrumented final44-case run, not an equivalent-work/statistical benchmark:

| Phase | Seconds |
| --- | ---: |
| Original setup | 9.248 |
| Original assertion bodies | 8.836 |
| Native extraction | 0.130 |
| New independent capsule projection | 0.010 |
| Embedded initialization/admission/fact+scope loading | 13.778 |
| SQL setup/querying | 12.475 |
| **Complete relational phase** | **26.393** |

For new32 specifically: original setup+body5.783s versus relational18.185s. That is currently
SLOWER. No suite speedup claim; more authority coverage increased the relational overhead.
Native extraction itself remains tiny. Fresh per-case schemas, admission/signatures and
expanded view/query planning/evaluation are included; their individual causal shares have
not been profiled. Amortization/materialized obligations look worth investigating, but must
preserve the packet/context distinctions that just exposed the oracle bug.

## Evidence and disposition

Ignored worktree evidence: `build/relational-spike/authority-smoke/`, `authority-v1/`,
`authority-gap-fix/` and `authority-final/`. Final case reports retain baseline counters,
observed scopes, independent original verdicts, raw decoded facts, projected headers/errors,
root manifests, DuckDB files, rule labels, timings and unchanged-data assertions. Existing
source SHA256/base-byte checks and groups/summary are retained. Failed initial gate is not
relabelled green by the later pass.

The broader negative map now agrees, but replacement assurance is still incomplete and
this slice is not fast enough. Next proposal should focus on amortizing the test-oracle
materialization/query work with explicit identities/availability/context and sensitivity
controls, not removing original tests or weakening authority checks. No extra experiment,
production integration, service, publication or native19/VP-001 investigation follows this
report. Work remains isolated; older uncertainty is not diagnosed or waived.
