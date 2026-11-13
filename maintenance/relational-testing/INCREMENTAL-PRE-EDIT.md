# Incremental prototype — concrete pre-edit review

Status: READ-ONLY PLAN COMPLETE; awaiting gate acceptance BEFORE coding/build/test activation.
The user stated **“reviewed. GO”** for the [design](INCREMENTAL-DESIGN.md),
[example](INCREMENTAL-EXAMPLE.md) and [handoff](INCREMENTAL-HANDOFF.md). Owner: the current
coordinator/assistant session, ONLY isolated spike scope; no new agent or Iteration25 delegation.
GO approves the bounded prototype, retaining its pre-edit and later readiness gates, no commit/push.

## 1. Preservation, pins and provenance

Actual read-only observations:

- Spike HEAD `15555c01e4db19a20b4de7049f776c4d995bd5e0`; tracked diff against HEAD empty;
  pre-existing `spikes/` remains untracked. NEW `incremental/` directory does not exist yet.
- All372 tracked files inventoried by path/Git mode/actual size/SHA256; sorted-key compact ASCII
  JSON in `git ls-files -s` order has SHA256
  `6dfe866aa2fd13938a938260542240d8a55694e83103484c5adfff5d48583c3b`.
  The13 package entries' same-format digest is
  `49688a7f14b2962506d0a5b627e9ea7796f9e1a1b9352e6b78175ae65627fd97`.
  This is a current inventory, NOT reproducible-build proof or an artifact manifest already copied.
- Prepared `_core.abi3.so`:885112 bytes/SHA256
  `5fd0ce05a9bb48bb7bdcf2b7de212427f54522c37301e12e4ec7fc7f14fda134`.
  `_core_fault.abi3.so`:894192 bytes/SHA256
  `b3f8821144bf64cda49c9ecfaba282e6f88dcdf4517087fab046fa925520febd`.
  Fault extension is for original spike test imports only, NOT the controller/candidate foundation.
- Existing native setup/build logs identify worktree/nodownload/GCC15.3.0/Python3.13.15 and final
  core linking. SHA256s respectively
  `54cad84e42d9b4ae2df2741a43acbb15089309671992fe75f4f0824d1d98b47f` and
  `93c165b70e294ce7b5f06cbf8becba3cd36ebba93aaceec0e07cb4291cb20d13`.
  Warnings remain. Those logs do NOT cryptographically establish that current binary came from
  current source; no signed source-to-artifact receipt/reproducible rebuild is claimed.
- Selected eight old source hashes agree the retained `parallel-replay-v1/final-audit.json`:
  exercise/normalizer/checker/checks/schema/engine/test_spike/run. Original files remain untouched.
- Python resolves to `/nix/store/jy00n3jp5xj8s40n1fbldmkcr5n7avxc-python3-3.13.15/bin/python3.13`,
  SHA256 `85ee2b9c856b1bd76c8ba64b2d5081456dec55b1404a785674faa542ed2ba4a5`;
  interpreter inspection reports3.13.15/GCC15.3.0, Linuxx86_64/kernel6.18.55.
- DuckDB CLI resolves to `/nix/store/ck8gcahsxids1hs72wrb8xqc00l044qn-duckdb-1.5.2/bin/duckdb`,
 69863400 bytes/SHA256 `e098062c23f5005743d09c689c72e5e0ef6cbce22834836fa814cf4a564d6206`.
  Version here derives from store identity, NOT fresh CLI activation. Python+CLI Nix runtime closure
  query yields23 unique paths/sorted newline-list digest
  `46597d1096ffc9e523341ab414fb12cf29fed76bff84b017e03f2e8c7a1a261d`;
  a path-list digest is NOT the digest of every runtime file.

Static ELF review found core's RUNPATH begins `/work/repos/micha/dml-design/outputs/out/lib`
(currently ABSENT), followed by immutable glibc/GCC paths. Only core NEEDED library is libc.
Do NOT trust this mutable search entry or patch the ELF. Future process environment explicitly
sets LD_LIBRARY_PATH to the exact glibc/GCC paths below, rejects LD_PRELOAD/LD_AUDIT/ambient
library overrides, and checks actual loaded core/libs from process receipts before admission:

- glibc directory `/nix/store/fsd4vbp9zjd9iaicq2fb9lpc1h5j973y-glibc-2.42-100/lib`;
  libc SHA256 `43a0b688667ef6e98cb18870c593b695eb63f4b23a6468b4821cd176b4407633`;
  loader SHA256 `3a6e6f399324848162b0af1b3709889ada1122436d770af3a0d8f7a6df5623f8`.
- GCC directory `/nix/store/dqj57l1prad38vjrad4bs9d977i4q5zm-gcc-15.3.0-lib/lib`;
  libstdc++ SHA256 `c7a8b46b4a8fc28d781e559ec1d3ace35b1ecb4bc38d6032374b36cdcfddb773`;
  libgcc resolves to `/nix/store/0vw7gvcazcjqc762x7vg3l31cpx65l7i-gcc-15.3.0-libgcc/lib/libgcc_s.so.1`,
  SHA256 `3229a31b1f26283f7e81e2567155e532fbebef55237bff771f0d73a8cf9fe5d1`.

After gate acceptance: prepare NEW owned snapshots under `build/relational-spike/incremental-v1/`
using verified copies of package/artifact/stage bytes, and retain full manifests, not just these
summary hashes. Trust is pinned as-built bytes + independently reviewed bootstrap controls,
qualified by historical build provenance, not promotion to a general controller. No native rebuild.
Controller/candidate processes use absolute Python with `-I -B`, explicit importlib package paths,
minimal environment (fixed locale/hash seed/owned HOME+TMPDIR, exact library/PATH pins), no ambient
PYTHONPATH/site customizations. PATH exposes only pinned DuckDB for old engine lookup. Record actual
module paths/hashes and loaded relevant libraries; no whole environment dump or secrets. No claims
of hostile-code containment or complete environmental capture.

## 2. Dependency graph and NEW module scope

NEW code only under `spikes/relational_invariants/incremental/`:
`identity.py`, `artifacts.py`, `records.py`, `stages.py`, `driver.py`, `test_identity.py`,
`test_artifacts.py`, `test_records.py`, `test_evidence.py`, `README.md` (names refinable).
Read-only old payload copies live in owned ignored snapshots. No old file or maintained API edit.

Controller namespace pins new identity/artifact/record/driver code plus frozen low-level recorder
package/core/runtime. Stage execution wrapper bytes belong to each affected stage. No checker-byte
change in the controller namespace: it is declared payload, not imported into the recorder.

- E: candidate whole372-file manifest + explicit native artifact/runtime; frozen `exerciser.py`;
  new E-wrapper code; two-checkpoint3-position scenario, normal/wrong-result variant, seed policy,
  export contract and all applicable limits. Candidate B is A's owned copy with ONE appended
  comment in `builtin.py`; still whole-manifest different, no compiler invoked.
- P: E key + selected evidence digest; new import/extraction/materialization wrapper; frozen
  decoder package/core/`transfer.py`, `normalizer.py`, `schema.py`, `engine.py`, DuckDB/runtime;
  ordered native roots/expectations and all applicable limits. P2 changes an actual comment in
  its owned normalizer copy; do not merely change a revision label.
- C: P key + selected projection digest; new checking wrapper; frozen `checker.py`, `checks.sql`,
  `engine.py`, DuckDB/runtime; independently pinned assertion manifest/expected scope and limits.
  C2 changes an actual comment in its owned checker copy. Transitive views ALL in `checks.sql`.

Canonical envelopes permit null/bool/I64/string/list/string-key objects, explicit artifact
SHA256 references, no floats/implicit Python values/duplicate keys. Hash domain prefixes
`incremental-v1/E|P|C`, format revision and namespace are mandatory. Reject missing/unknown
manifest fields, file-set disagreements, unsafe relative names/symlinks and same-description
identity conflicts. Operational output directories/timestamps/PIDs never partition computation
keys; actual producer occurrence stays in evidence/result authority. Fresh evidence manifest
includes THIS attempt's occurrence even if portable candidate content is byte-identical.

## 3. Portable custody and limits

Static review confirms public [export/import](../../../dml-relational-spike/docs/spec-next/transfer.md)
handles arbitrary native-valid DAG histories; no private codec or fake executable packet is needed.
Handles MUST close before transfer helpers; one store owner at a time. No database/lock copying.

E closes its actual native scenario, exports EACH ordered manifest root independently (normal3,
wrong-result4), preserving fork-only history and checkpoint expectations. Write distinct portable
bundle files and root/expectation/error/actual-loaded-code receipt, stdout/stderr, true exit.
Controller validates completeness/bytes/root association, not semantic SQL truth. Native import
validation uses pinned transfer decoder, not assertions supplied by candidate. P imports every
bundle into ONE new OWN case store with explicit `root-i` refs, closes each import, verifies
returned root against manifest, then invokes old extraction once across all declared roots.
No original/retired fixture read, root omission or graph-root value inference.

Limits unchanged: native transfer32MiB envelope/4MiB record/16MiB packed/100000objects per bundle;
normalizer10000 unique typed objects; builtin64/16/16 and existing trace≤16. Proposed NEW admission
cap32MiB summed stage evidence files plus1MiB total logs (fail/preserve overflow; not truncation-as-
complete). More than four E roots rejected. No raised existing bound. Exact future native counts/
export sizes measured during approved activation; unexpectedly exceeded bounds STOP, no auto-growth.

P retains closed `facts.duckdb`, every JSONL/schema/root context/stats/receipt. C copies ONLY this
closed analytical database to its OWN scratch database (NOT LMDB), runs original checker there
which creates views, and never writes P's artifact. Retain ordered violations/inventory/receipt/logs.
Hash P before/after C. Artifact manifests enumerate every file by safe relative name/size/digest,
record producer/key/dependencies/exit, then finalize by rename within same owned parent. Selected
files rehash on reuse; `.partial`, missing/unlisted/symlink/tampered content fails closed. Incomplete
files/orphans never selectable. Atomic filesystem rename + DML ref publication is not cross-system
atomicity or crash-durability/fsync proof; explicitly retain this limitation.

## 4. Exact ordinary controller conventions

All NEW roles use `spike-incremental-*-v1`, native ordinary DAGs rooted at their STRING role
literal. Scalar fields are literal datums; graph links are subdag nodes; canonical manifests are
BYTES containing the above JSON. Exact field sets/types checked, no executable opaque plugin schema.

| Role | Fields in addition to role |
| --- | --- |
| request | occurrence STRING, stage STRING, key STRING, control STRING, inputs BYTES, basis BYTES(commitID) |
| attempt | occurrence STRING, request SUBDAG, state STRING(running/done), outcome NULL or SUBDAG |
| outcome | attempt-occurrence STRING, status STRING(success/rejected/error), artifacts BYTES(manifest), exit I64, diagnostics BYTES |
| satisfaction | request SUBDAG, attempt SUBDAG(terminal OLD), outcome SUBDAG |
| selection | stage STRING, key STRING, attempt SUBDAG, outcome SUBDAG |
| allocator | store-namespace STRING, next-run I64, next-event I64 |

No cycle: initial attempt has NULL outcome; outcome names the occurrence, not terminal attempt
ID; terminal attempt links outcome and original request. Selection/satisfaction link terminal
attempt/outcome. Old initial/terminal descriptions share occurrence, not content identity.
New commit keeps selectors plus `latest-event` (old events retained through single-parent history),
not an ever-growing live tree for every event. Known slots `sel-E|P|C-<64hex>`; max16 selectors total,
no history discovery or generic table. A named branch ref selects one snapshot. Writer reads actual
branch basis in SAME write transaction, checks expected basis, copies unrelated tree entries,
writes new event/selection and updates ONLY that ref. Stale basis rejects; no overwrite fallback.

Serialized allocator ref is independent of branch selection: transactionally reserve run/event
sequence on canonical allocator, then record request/initial attempt BEFORE stage activation.
One explicit NEW store namespace plus reserved run/event numbers distinguishes actual events;
branch forks never reset it. Gaps after interruption acceptable, duplicate fresh identity not.
Stable checkpoint/call labels are comparison labels ONLY. Occurrence schema not a public DML API.

Outcome publication follows artifact verification/true exit. Unknown/error/rejected terminal
attempts stay unselected. Reuse resolves ONLY exact known slot, revalidates role/key/links/producer/
artifact/dependencies and records own satisfaction; found-invalid never becomes miss/fresh fallback.
Explicit `adopt(stage,key,terminal,expected_basis)` verifies success and changes one selector in a
new snapshot, separate from fresh completion. Branch round5 vs round6 E choices preserve all other
selectors. Controller records never enter candidate repositories. Candidate return channel only
supplies declared artifacts; never grants selection authority or controller-store access by API.

## 5. Activation/ownership counts and wrong-result boundary

Seven-round story stays21 requests/15 fresh attempts =4E5P6C, six reuses. Round7 rejected C
is required by outer assertion, retained as rejected/nonzero, NEVER selected positive success.
Specific bad-operation subject is independently determined from native mutation receipt and
compared with `map_get_value`, not passed into SQL filtering as an answer.

Each E/P/C is an owned foreground Python process. E has no grandchildren; P old materializer
invokes one DuckDB CLI; C old checker invokes three sequential DuckDB CLI commands. Thus story
has15 stage processes and23 DuckDB invocations, if unchanged payload command counts hold.
These are NOT LOCAL application jobs or detached services. Driver waits each stage; wrappers wait
all CLIs. PID/parent/group/command/start/true exit receipts and logs retained. Parent death with
unknown child disposition stops; no auto-resume/retry. OS/network adapter APIs not in dispatch;
only pinned Python/DuckDB executable allowlist. No new timeout policy or runtime weakening.

## 6. Assurance map

Existing test_spike covers values/sources/positions/fork, unique extraction, actual wrong native
result, missing root, nine SQL faults and checker independence. Original assertions/body bytes
remain exact; later complete spike collection also keeps all paired/authority/isolation controls.
SQL scope is still partial: no independent native hash/codec proof, every role/URI/name/budget,
mutable ref observation history, real LOCAL custody/deadline/transport or scientific correctness.

New direct checks cover keys/transitive identities, namespaces/occurrences, state/ref publication,
manifest admission, selected producer/dependency links and explicit adoption/branches. SAME retained
story is independently inspected without stage replay. An isolated disabled `map_get_value` branch
on round7's retained facts must make the outer expected-rejection assertion fail; this deliberate
non-success is sensitivity evidence, never greenwashing. Historical/cached coverage labelled OLD,
not merged as fresh instrumentation or a100% maintained-gate substitute. Diagram stays unchanged:
ordinary DAG roles, no new native entities/layout/storage relationships.

## 7. Finite validation / gate sequence

Proposed after pre-edit acceptance:

1. Implement NEW files, static/pure controls; one focused new-controller test invocation with NEW
   output/XML/basetemp. Tiny real bootstrap/storage controls use ONE owned store and ONE portable
   seed (simple literal/DAG/tree/commit, ZERO map/get/E-P-C story activation). Permit owned separate
   stores for import/ref rollback negatives; no compilation/dependency installation. Pure/admission/
   occurrence/branch/unknown/failed/tamper/stale-basis cases use explicit CONTROL namespace, cannot
   supply acceptance selections. Exact new test list/count frozen before invocation, no surprise
   fixtures. Failed meaningful control stops for causal review, not automatic repeat.
2. Freeze controller/variants/pins/new source, then independent STATIC readiness + tiny bootstrap
   evidence review. No seven-round activation until explicit readiness acceptance.
3. ONE seven-round story, one new immutable output tree; successful-path counts above only. No
   automatic second story. SAME blocked reader review and finite sensitivity over retained negative
   P data (one owning-rule-disabled C invocation, separate CONTROL attempt/not adopted; three CLI
   commands). Any extra future fixture/activation needs named review first.
4. ONE complete isolated spike collection, on final sources, no shared maintained gate:
   `python -m pytest -q --noconftest spikes/relational_invariants --basetemp=build/relational-spike/incremental-final-cases --junitxml=build/relational-spike/incremental-final.xml`.
   Use cached pytest/Hypothesis/site-packages and isolated existing DuckDB Python binding via explicit
   test-only PYTHONPATH, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1`, pinned libraries,
   `DML_BIN=.../build/spike-native/dml` import hint ONLY. This test environment is separately pinned;
   NOT candidate/controller isolated-process environment. No full maintained suite or DML native build.
   Original spike suite includes its own fresh fixture exercises, separately reported; the4E5P6C
   allowance describes the seven-round story, NOT all original test fixtures.
5. Freeze/review results, raw logs/XML/true exits/counts/owned disposition; STOP. No commit/push or
   main integration/controller trust promotion. Meaningful failures need scoped causal response,
   never automatic rerun. No coverage thresholds/exclusions/assertions/deadlines/budgets changed.

Pure controls proposed: each E/P/C dependency mutation, equal-output/different build, P-key chain,
checker outside namespace, unknown field/types/duplicates/path/symlink/file-set/conflicting identity,
operational path neutrality, fresh run-label separation. Real controls: bootstrap storage/ref abort/
readback, native portable import/root mismatch/missingroot, running/failed/rejected selection,
terminal occurrence/request/outcome cross-link swap, explicit adoption/stale basis/old branch,
artifact tamper/missing/partial/unlisted entry. No full chain in focused fixtures.

## Review request / current stop

Accept (or revise) this concrete isolated pre-edit plan, particularly **qualified as-built native
pinning**, **portable multi-root evidence**, **spike-only controller schema**, and finite focused/
readiness/story/final-collection validation. No source/implementation/evidence output directory has
been created by this read-only phase; no DML/native import/test/CLI activation/build/install occurs.
Only design-context documentation changes. Two early guessed transfer-doc paths returned ENOENT;
correct `docs/spec-next/transfer.md` was subsequently read, no missing API diagnosis implied.
GHA disabled/native19 PAUSED/private candidate retained/VP001 OPEN UNKNOWN/Iteration25 ownership
untouched. Gate acceptance pending; implementation GO is active only subject to that gate.
