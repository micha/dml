# Candidate gate follow-up: immutable apply inputs

## Verdict and authority boundary

**The narrow gate now resists the reproduced plan-path substitution, uncaptured
expression and unexported-creation attacks.** This is not general retention-safe
deployment. Linux sealing fixes the checked-plan-versus-reopened-path gap; it does
not make apply atomic or authorize arbitrary provider Delete operations.

This report records candidate experiments, not approved DML policy or APIs. The
research journal in [gate.py](gate.py) remains explicitly **fake**. The public real
journal bridge remains negative integration evidence, not joined cleanup. No DML
implementation, shared tool, other worker or cloud resource was modified.

The independent [hardening review](../hardening-review/report.md) found flaws in
the initial delivery. Before editing, every original source/report/result/marker
was preserved byte-for-byte under `*-initial` names, indexed by
[initial-checksums.json](initial-checksums.json). See [report-initial.md](report-initial.md),
[gate-initial.py](gate-initial.py) and [test-results-initial.json](test-results-initial.json).
The historical report's original links remain unchanged; use the checksum index
for the corresponding historical code rather than its links to now-revised files.

## Exact reproduction, versions and evidence

From the design repository:

```sh
python3 -B feasibility/gate/followup_tests.py
# Regression alone, without replaying the preserved attacks:
python3 -B feasibility/gate/run_tests.py
```

The final combined run passed:

| Evidence unit | Count and boundary |
| --- | --- |
| Current regression groups | **28**; actual CLI/journal/crash probes plus receipt checks |
| New adversarial groups | **22**; kernel/CLI/preflight checks, including four helper/mock groups |
| Historical attack replays | **4**; unchanged initial gate, fresh synthetic resources |
| Actual OpenTofu CLI invocations | **285**, including the regression's **130** |
| Wrapper CLI subprocesses | **3**, invoking plan/reserve/apply independently |
| Abrupt OS exits | **2**, before dispatch and after cleanup before outcome publication |

These are different units. The combined evidence is
[followup-test-results.json](followup-test-results.json); regression-only results
are [test-results.json](test-results.json). The retained final sandbox is
`runtime/followup/run-b51b898c/`. Four combined runs and one standalone regression
run are retained, including two harness failures: a historical exception class
was initially caught as the new class, and a targeted-plan rejection happened
earlier than the asserted diagnostic. Their sandboxes remain; no gate check was
weakened to resolve them. Each follow-up runner caps its own runs at eight and
never prunes the seven initial sandboxes.

Versions: Python **3.13.15**, SQLite **3.51.2**, Linux **6.18.55**, OpenTofu **1.13.2**,
built-in `terraform_data` only. Every CLI invocation verifies the official shared
archive SHA-256
`723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5`
and executable bytes. No tool installation/provider download was needed.

All six executed source checksums are in [code-checksums.json](code-checksums.json)
and the combined results. Principal SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `gate.py` | `37f33708aef5ef78a8fec32d466b04aa46602d7f8c5ff1f2cebc4d464cdb5afb` |
| `apply_input.py` | `651bfe485502122c461e41588b479a96ead10d50ede7b09d03a536d4f7b3fa8f` |
| `fixture_language.py` | `c768e80f5536e2443bd449497374ebdec04fa528834fe79d54a948b9448e94eb` |

## Fix 1: apply the checked byte object

[apply_input.py](apply_input.py) opens the source once, reads a bounded byte object,
verifies its expected digest, copies it to `memfd_create(MFD_ALLOW_SEALING)`, then
sets **WRITE, SHRINK, GROW and SEAL** seals. It verifies the kernel seal mask and
transferred digest. Errors, unsupported sealing or unavailable memfd reject
admission; there is no mutable-file fallback.

The same sealed object is used for plan JSON inspection, both admission checks,
and `tofu apply /proc/self/fd/N`, with Python `pass_fds=(N,)`. The original pathname
is not reopened after validation. The descriptor closes on normal return/error.
A digest of a mutable file followed by apply of that pathname is no longer the
implementation.

Executed comparison: the unchanged gate's targeted-delete ticket excluded an extra
retained UUID, but swapping its pathname at `before_effect` destroyed both UUIDs.
The revised gate's final-check barrier swaps a normal cleanup plan with an actual
all-resource destruction plan. It also attempts write, shrink, grow and seal
changes on the live approved object. All four operations return **EPERM**, mask
**15** remains, and the replacement pathname has a different digest. Actual apply
still deletes only the approved victim; the extra retained UUID remains identical.
This approved plan removes the victim declaration while exporting the survivor.
The original targeted-destroy form is separately rejected before apply because
its planned census omits a surviving resource.

A swap before snapshot acquisition rejects before any manager CLI call. A
configuration change at the public final-check barrier is also rejected before
apply by a final material check. That extra check is not an atomic defense against
arbitrary concurrent configuration writers.

## Fix 2: validate census before effects

[fixture_language.py](fixture_language.py) requires every declared managed resource
to appear exactly once in `dml_manifest`, under its own address and exact resource
ID expression. Missing output, empty mapping with resources, extra/unexported
resources, wrong ID expressions and duplicate JSON keys reject before planning.
An empty resource set with an explicit empty manifest remains valid for cleanup.

The saved plan is checked independently: its captured fixture configuration,
resource changes, expected surviving/created addresses, planned resource census,
and known/unknown output-ID fields must agree. The ticket binds before/after
census alongside exact plan/material digests, UUID victims, manager lineage/serial
and snapshot digest, root/membership revision and durable reservation.

Historical replay creates a hidden resource before the old receipt rejects it.
The revised test rejects the same extra declaration with **zero planning CLI
calls** and unchanged state. A positive creation test exports both resources;
admission handles the new ID's deliberately unknown plan value and validates both
actual IDs afterward. Two deliberately modified in-memory plan documents test
missing unknown-ID and saved-configuration census rejection. Those two are helper
checks, not manager attacks.

## Fix 3: reject uncaptured evaluation

Restricted JSON was not safe HCL. The new whitelist supports only ASCII fixture
labels, string variables/defaults and captured string tfvars, literal strings,
exact `${var.name}` resource inputs, exact `${terraform_data.name.id}` manifest
entries, and boolean `prevent_destroy`. Unknown variables/inputs, interpolated
functions, template directives and sensitive declarations are rejected. It is a
small accepted fixture language, not a universal semantic parser.

The unchanged gate accepts `${file("input.txt")}` and ignores a subsequent change
to that uncaptured file. The new gate rejects it before planning. It also rejects
`${sensitive("SYNTHETIC-ONLY")}`, expression defaults and unknown tfvars before
planning. Existing variable/resource-ID fixtures still pass all regression and
positive cleanup cases. Two injected missing/denied-sealing tests demonstrate
fail-closed control flow; the host actually supports sealing, so these are mocks,
not evidence of portability to another kernel.

## Observations, crashes and journal boundary

Current CLI logs contain argv, exit status, passed descriptor numbers and output
lengths, **never stdout/stderr bodies**. State/plan/output JSON is returned in memory
for local checks, not persisted into those logs. Logs are mode **0600**, fixtures
mode **0700**, and subprocess umask **077** restricts manager state. Historical
synthetic raw observation logs/state were restricted without changing their bytes.

There is no secret detector: a test deliberately puts a literal synthetic marker
in manager state and confirms the body is returned in memory but absent from
metadata logs. State still contains the plaintext; inputs, paths, identifiers,
metadata, lengths and state hashes can themselves be sensitive. Owner-only modes
are neither encryption nor physical erasure, and cannot protect against the owner
or privileged processes. Historical replay logs intentionally retain synthetic
raw values under restricted permissions.

The regression still demonstrates durable `unknown` across actual process exits,
blind-retry rejection, coherent versus mixed receipts, retained UUID update/replace/
destroy rejection and cooperative writer exclusion. Sealed memfds are volatile:
a crash can lose the approved bytes even though the reservation/hash survives.
Recovery therefore needs independent immutable plan retention or authoritative
outcome investigation, not guessing replacement bytes from a digest. Mid-provider
operation interruption is still not tested here.

The real `journal-v2` probe still derives retention from stored commits/heads,
rejects stale membership and fences publication. It rejects the UUID-to-file
physical bridge. In a deliberately mismatched independent manager effect, successful
apply does not satisfy file absence acknowledgement; durable `intent` remains.
The file journal's own cleanup resolves it. Positive adapter apply remains
unsupported and unexecuted; these changes do not silently make it joined cleanup.

## Limits, alternatives and next experiment

Sealing freezes plan bytes, **not provider implementations, provider effects or
Delete authority**. An ungated direct CLI remains a bypass. Manager locks do not
cover research publication; cooperating deployers/publishers must honor the durable
fence regardless of whether deployment uses local CLI, CI or another driver.
Long/unknown applies still sacrifice unrelated-work availability. The fake journal
still lacks authoritative roots, ownership, dependency closure, disposed-identity
publication rejection and a complete membership census.

Unsupported: full HCL, functions/templates beyond the whitelist, modules, arbitrary
providers/backends, imports, data sources, indexed/deposed instances, provisioners,
complex variables and external/ephemeral inputs. There is no hostile-process,
privileged filesystem or distributed lease guarantee. Receipts/bundles remain
sidecars rather than native immutable DML history. An isolated immutable execution
bundle could persist approved inputs across crash and transport, but would need a
separate demonstrated ownership/immutability boundary.

Next proposed experiment: retain provider-aware immutable bundles and record
receipts in versioned history, then require provider Delete to verify durable,
identity-scoped retirement authority. Reproduce forced replacement and death
around real provider effects. This is a proposal, not implementation approval.

Documentation is supplementary. Context7 quota was exhausted; primary
[Linux sealing](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html),
[memfd](https://man7.org/linux/man-pages/man2/memfd_create.2.html),
[Python OS](https://docs.python.org/3.13/library/os.html) and
[subprocess](https://docs.python.org/3.13/library/subprocess.html) docs were downloaded
under ignored runtime with checksums recorded. Broad backend safety remains
conjectural; the narrow conclusions above are tied to executed evidence.
