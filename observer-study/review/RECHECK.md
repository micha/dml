# Stage 0 correction recheck

## Current disposition

**Qualified pass for Stage 0. R1–R4 are corrected and independently verified.**
No outstanding blocking issue from the initial audit remains. This accepts the
small retrospective corpus with its explicit evidence gaps, not production safety,
complete historical capture, or authority to start Stage 1.

The [initial REPORT.md](REPORT.md), [focused_checks.py](focused_checks.py), initial
probe output and 29-test transcript remain unchanged. The historical disposition
there is intentionally still **needs correction**. This document records the later
correction/recheck; it does not erase the original eight unexpected acceptances.
The initial summary is retained as
`observer-study/runtime/stage0/reviewer-initial-summary.json` before updating the
current summary. The old current reviewer marker was removed while work proceeded.

## Independent commands and outcomes

All commands ran from `/work/repos/micha/dml-design`, with existing Python 3,
without installing tools, executing producer modules, or accessing cloud services.
[recheck_checks.py](recheck_checks.py) records each command's actual exit code,
validates its output, and checks preservation before and after the run:

```sh
mountpoint /work
python3 -B observer-study/review/recheck_checks.py
```

The recheck runner executes these documented commands itself:

| Command | Measured outcome |
| --- | --- |
| `python3 -B observer-study/corpus/corpus.py` | Exit 0, valid offline |
| `python3 -B observer-study/corpus/corpus.py --sources` | Exit 0, valid source reconstruction |
| `python3 -B observer-study/corpus/corpus.py --availability` | Exit 0, six explicit metadata observations only |
| `python3 -B observer-study/corpus/test_corpus.py` | Exit 0, **39 tests pass**, zero failures/errors |
| `python3 -B observer-study/review/focused_checks.py` | Exit 0, **16 required rejections / 16 correct / zero unexpected acceptances** |
| `python3 -B observer-study/corpus/check_review.py` | Exit 0, same 16/16 rejection result in an isolated mirror |
| `python3 -B observer-study/corpus/corpus.py --sources --availability` | Exit 0, valid final source check |

Additional wrapper trust check:

```sh
python3 -B observer-study/review/check_review_boundary.py
git diff --check -- observer-study/review
```

Both exit 0. The boundary checker records four synthetic child-response cases;
these are wrapper observations, **not four additional research trials**. Git's
check does not cover untracked content; final review-source syntax, whitespace
and local report links are validated separately before completion publication.

Generated outputs use separate names and do not overwrite initial results:

- [Preservation inventory and command results](../runtime/stage0/reviewer-recheck-preservation.json)
- [39-test transcript](../runtime/stage0/reviewer-recheck-tests.txt)
- [Live unchanged focused-check results](../runtime/stage0/reviewer-recheck-focused.json)
- [Mirror-check results](../runtime/stage0/reviewer-recheck-mirror.json)
- [Final source/availability check](../runtime/stage0/reviewer-recheck-final.json)
- [Wrapper trust observations](../runtime/stage0/reviewer-recheck-wrapper-boundary.json)

## Frozen package and historical preservation

The original reviewed manifest is still SHA256
`e390d5606f01a4f365ceb4d3c604877f7cc451339a5b555a581ddd9c5f9fde00`.
Using that already-recorded hash as the comparison baseline, the recheck verifies
**all 28 frozen files**: manifest, allowlist, 23 fixtures, ground truth, answer
sheet and gaps. Their bytes are unchanged from the initial audit, not merely
internally consistent with a newly regenerated manifest.

The allowlist hash remains
`12413b7fe40563d37cbcafb9452e7352f8e621640dbbdfdc728353bbd9a177c7`.
The unchanged independent focused checker is SHA256
`083e98039e9f54abfd08929a7c0327ce922ef7d5f8d1368c1603217bffa663d2`.

Independent reconstruction still verifies **23 originals / 183,588 original
bytes**, **99 selected rows**, **78 citation uses**, **ten historical digest
bindings**, and **69,976 fixture bytes**. Five scenarios, 17 facts and nine gaps
remain present. All six cited supporting paths are currently present: four regular
files and two directories; none of their contents were read. No new historical
IDs, receipts, availability events or substantive evidence claims were introduced.

The recheck hashes the initial report, unchanged checker, initial summary and all
six initial output files before and after testing; all agree. It also verifies
that the updated corpus root files and curator summary/marker are unchanged by
this review's test runs. The inventory records exact hashes. We do not claim an
initial hash baseline for every non-frozen implementation/documentation file;
those were reviewed against the initial findings and prior inspected code.

## Correction verification

### R1 — Closed

`observer-study/corpus/corpus.py`, `validate_source_format()` explicitly rejects
unknown source kinds and is called by both `check()` and `reconstruct()`.
`check()` now validates `stage0-gaps-v1` and requires answer ingestion to match the
retrospective manifest. Future kind/schema and contradictory ingestion are rejected
in both modes. The offline fallback-to-text path is no longer reachable for an
unknown kind. Regression tests explicitly cover both modes.

### R2 — Closed

`decode_json()` is shared by `load()` and `project()`. It rejects duplicate keys
and nonfinite constants before selection, including nested unselected fields.
Its `parse_float` handler also rejects numeric overflow such as `1e999`.
The original strictness mismatch is fixed without changing selected fixture bytes.
The unchanged reviewer probes reject both malformed original byte strings;
new corpus tests exercise nested ambiguity, infinities and overflow.

### R3 — Closed

`check()` requires each scenario's `facts` to be a nonempty list before checking
per-fact citations. All five empty-scenario mutations are covered in both modes;
uncited facts are rejected. The change does not freeze a universal fact count or
claim automatic verification of arbitrary prose. The original readable/structured
answers remain unchanged.

### R4 — Closed

`validate_source_format()` requires a non-boolean integer length in the bounded
range 0–256 KiB. `reconstruct()` compares that length with actual original bytes
before hash comparison. Unit fields must be nonblank strings. New regression
coverage includes booleans, fractional/string/list counts, out-of-range counts,
plausible-but-wrong positive lengths, and malformed/blank units.

The original hash-tamper test now uses **same-length wrong bytes**, preserving the
hash-rejection test separately from the new length rejection. It was not weakened.
Current originals still match their historical/frozen digests; no source was
refreshed to make the check pass.

## Review of `corpus/check_review.py`

**No blocking ownership or actual false-success issue found in the measured run.**
Its implementation is suitable as a scoped pre-publication test runner, with the
trust limits below. It is not itself independent review acceptance.

### Ownership and acquisition

- It validates the corpus/source projections first, then copies only the explicitly
  enumerated corpus files and 23 allowlisted originals using bounded no-follow reads.
  It does not import/execute historical producer modules or load producer runtime
  state, logs, sessions or pinned primary-source bundles.
- It copies the reviewed independent checker into a newly created corpus-owned
  temporary mirror. That known checker is intentionally executable test code,
  not imported research text. Copying bytes into a mirror does not amend `review/`.
- `put()` validates relative paths and uses exclusive file creation. The mirror
  starts empty; copied inputs cannot introduce symlink traversal through its tree.
  These are safeguards for this enumerated test runner, not a general sandbox for
  untrusted executable code.
- The child derives its ROOT from its mirrored script path, so its `reviewer-probe-*`
  scratch is inside the mirror. Temporary directories are cleaned. Before/after
  hashes show no real reviewer outputs, corpus root files or curator marker changed.
- The mirror's synthetic marker/summary are clearly labeled
  `validation-input-only-not-completion`. The wrapper does not publish them into the
  live Stage 0 directory. Their three hash checks establish fixture consistency,
  **not live curator completion**. The separate live focused rerun verified the
  actual updated report/summary/marker hashes.

### W1 — Low, nonblocking: wrapper delegates result truth to the child

**Locator:** `observer-study/corpus/check_review.py`, `main()` after
`subprocess.run()` (JSON decode, annotation and return of `process.returncode`).

The wrapper decodes child JSON and returns the child exit code; it does not itself
require 16 rejections/zero acceptances or compare the reviewer script with the
initial externally recorded hash. Its `unchanged_review_bytes` means copied bytes
still equal the bytes read for this invocation, not historical-source authentication.

[check_review_boundary.py](check_review_boundary.py) mocks only the subprocess
response, without changing the reviewed script or wrapper. Observed outcomes:

1. Zero exit with `{}` returns zero despite missing rejection fields.
2. Zero exit with 16 unexpected acceptances and zero correct rejections also returns
   zero and retains those contradictory fields.
3. Nonzero child exit propagates as nonzero.
4. Malformed child JSON is rejected by strict decoding.

**Interpretation:** this is a trust/defensive-validation limitation, not evidence
that the actual child produced a false pass. The actual unchanged checker correctly
returns nonzero for unexpected acceptance. This recheck independently pinned its
hash, ran it live, and required every one of the 16 result rows to be rejected;
the mirror produced the same result. A compromised/replaced test executable is
outside the package's stated attacker-resistance guarantee.

Optional hardening is to validate the child's result shape/counts and, when claiming
continuity with a previous review, compare against an independently supplied
expected script digest. Continue labeling mirror output as pre-publication fixture
validation rather than live completion or independent acceptance. This optional
hardening is **not a reopened R1–R4 blocker** and does not require later-stage work.

## Evidence limitations and scope remain unchanged

The initial A–E semantic review still applies because all frozen evidence and
answer files are unchanged. Adoption preservation remains a reported assertion
without numerical digest/inode/mtime pairs; exact reuse counts remain source-derived;
real disposal recovery is not a complete research computation/cleanup timeline;
AWS remains reported source inspection, not cloud-tested or newly primary-source
verified; real missing/excised datasets are not fabricated from synthetic tests.
Hashes are not authenticated historical attestations or complete closure capture.

No corpus, feasibility, root/design document or DML implementation was edited by
this reviewer. No commits, pushes, delegation, installs, services, cloud calls,
producer reruns or later stages occurred. Documented tests and the wrapper use and
clean their existing ignored corpus-owned scratch; persistent outputs are only
review source/reports and `runtime/stage0/reviewer-*` artifacts.

**Stop at Stage 0.** Qualified acceptance of this curated package does not authorize
Stage 1 or remedy the recorded research/resource-management flaws. Later work and
any stronger evidence acquisition require separate user/coordinator steering.
