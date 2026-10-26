# Stage 0: small retrospective evidence corpus

Status: **finished with gaps; R1–R4 corrected, awaiting acceptance review**. Stage 0 only. No graph
convention, model repository, reader/navigation contract, renderer, UI, live replay,
second producer or production integration was implemented.

## Read and validate

From the design repository root, with existing Python 3 (standard library only):

```sh
python3 -B observer-study/corpus/corpus.py
python3 -B observer-study/corpus/corpus.py --sources
python3 -B observer-study/corpus/corpus.py --availability
python3 -B observer-study/corpus/test_corpus.py
# Before publishing the real completion marker:
python3 -B observer-study/corpus/check_review.py
# Once a current completion marker exists:
python3 -B observer-study/review/focused_checks.py
```

- Default: offline package integrity, selection/citation consistency, units/classes,
  occurrence boundaries and historical digest bindings. Original runtime evidence
  is unnecessary. A missing original is not silently replaced with today's bytes.
- `--sources`: bounded read-only verification of the **23 frozen original paths**
  and byte-reproducible projections. Changed, missing, restricted or unsafe sources
  fail explicitly. This regenerates fixture bytes in memory; it runs no study code.
- `--availability`: six explicit supporting-path metadata observations only. It
  does not load directories, logs, snapshots or provider state. Output is a **new
  current observation**, not an update to the frozen availability record.
- Tests: 39 focused local corpus checks; not 39 research trials. Temporary synthetic
  mutations live only in ignored `runtime/` and are removed by the tests.
- Independent checks: [check_review.py](check_review.py) copies the unchanged reviewer
  script and only enumerated inputs into a corpus-owned temporary mirror. Its
  validation-only marker satisfies the reviewer's hash-input dependency without
  publishing real completion before tests. It rejects all 16 malformed probes;
  the normal live reviewer command is a post-publication confirmation. Neither
  mode runs producer code or modifies `review/`.

## Bounded corrections after independent review

The original review found all A–E mappings substantially truthful but exposed
R1–R4. Its findings are retained unchanged. This correction changes only validator,
regression tests, checking support and reports; the frozen manifest, allowlist,
fixtures, answer sheet, ground truth and nine evidence gaps remain byte-identical.

- **R1:** finite source kinds and gap schema are explicitly required offline and
  with sources; answer ingestion must agree with retrospective manifest ingestion.
- **R2:** one strict byte decoder handles both acquisition and package JSON.
  Duplicate keys and nonfinite values (including numeric overflow) are rejected
  anywhere in originals, including unselected fields, before projection.
- **R3:** each A–E scenario requires a nonempty list of cited facts. No universal
  fact-count rule or general prose-truth verification was added.
- **R4:** original byte counts must be non-boolean integers within 0–256 KiB,
  and must match actual byte length with `--sources`; units must be nonblank strings.
  Scientific meaning is not inferred from arbitrary unit prose.

Start with [ANSWER-SHEET.md](ANSWER-SHEET.md), [ground-truth.json](ground-truth.json),
[gaps.json](gaps.json), [manifest.json](manifest.json), and [REPORT.md](REPORT.md).
The readable sheet links directly to frozen selected evidence. JSON citations
contain original path, original full-file SHA256, JSON pointer or exact line range,
fixture pointer, and canonical selected-value SHA256. `fixtures/` is **not** a graph
convention: each file is merely a source-specific selected-copy envelope.

## Ownership and source of truth

The user assigned this worker only `observer-study/corpus/` and
`observer-study/runtime/stage0/curator-*`. Producer evidence under `feasibility/`
remains read-only and authoritative for what it reported. The curator owns this
selection recipe and interpretations; the coordinator owns experiment index/status,
and an independent reviewer owns acceptance. The DML implementation/specifications
were not touched. No commits, pushes, installs, research cloud operations, services,
credentials, session sweeps or study reruns were performed.

[allowlist.json](allowlist.json) freezes original hashes, byte lengths, explicit
selectors, sensitivity boundary, ten historical checksum bindings and six bounded
availability observations. [freeze.py](freeze.py) contains the reviewed source and
answer definitions. Its `--initial` mode refuses an already frozen corpus. It is
an authorship/bootstrap tool, **not a refresh command**; use the checker for normal
reproduction. Full refreeze into an isolated owned test directory is byte-compared
by the tests. It requires the same original bytes and metadata availability; the
frozen package itself survives disappearance of ignored supporting paths.

Changing source definitions, answers or frozen hashes requires an explicit new
curation/review, not a silent historical refresh. Manifests are not signed and are
not a tamper-proof trust root against an attacker who can replace the entire
package/checker. Tests rehash manipulated files to ensure semantic citation checks
also detect inconsistent locators, digests, evidence classes and historical bindings.
They do not prove the meaning of arbitrary authored prose.

## Selection and sensitivity

The package contains 23 **selected** snapshots, totalling 69,976 bytes. Only curated
reported JSON fields and safe source-code/note line spans were copied. Ordinary
`local_file` synthetic before/after strings and synthetic `.tofu.json` literals are
retained because they were explicitly inspected and non-secret. Most unrelated
result groups, manager projections and body/state fields were omitted. There is no
heuristic claim that strings without secret-looking patterns are safe.

Unknown sensitivity defaults to metadata-only. Raw provider state, session
transcripts, logs, SQLite databases, executable tools and runtime source bundles
were not opened/imported. External URLs remain locators, never automatically fetched.
The AWS primary-source trace is **authored source-inspection evidence**, not a new
inspection of the ignored pinned source copies and not a cloud test. The six original
supporting paths were present at Stage 0 lstat; no genuine missing/excised dataset
was discovered or invented. Missing/unavailable originals are tested synthetically,
not presented as historical findings.

File reads are bounded to 256 KiB, regular single-link files, and component-relative
`O_NOFOLLOW` opens. Absolute/traversing paths, parent/leaf symlinks, hardlinks, FIFOs
and oversized inputs are rejected. Metadata uses no-follow stat and never loads
contents. No HCL evaluation, script imports from feasibility, arbitrary URI reads,
provider execution or directory enumeration of runtime is involved.

## Provenance and interpretation

- Acquisition is **retrospective**. Source IDs identify curated copies, not past
  execution/request/attempt IDs. No historical occurrence IDs or timestamps were
  created. Content hashes and occurrence identity remain separate.
- Archived vulnerable gate and journal-v1 bytes were matched to reported historical
  manifests. Current gate/helper/audit source matches reported hashes separately.
  Original current sources were not relabelled as historical v1.
- A digest match establishes byte equality to a **reported digest**. It does not
  authenticate original authors, prove an experiment ran, guarantee independence,
  establish complete environment capture or validate scientific conclusions.
- Tool/kernel versions and executable hashes are retained only when supplied in
  selected historical evidence. Today's Python is not historical environment
  capture. Tools themselves were neither run nor rehashed during curation.
- Claims are curator-authored interpretations with separate citations, evidence
  classes, units, harness results, tested-system outcomes and limitations. Passing a
  counterexample harness may demonstrate an unsafe system.
- Numerical adoption digest/inode/mtime pairs, complete occurrence object streams,
  actual excision, and a real end-to-end request/computation/cleanup timeline remain
  unavailable in the allowed evidence. Simulation and real disposal streams are
  not spliced into one invented execution.

## Retention and privacy

This corpus retains safe **copies** of selected evidence. It neither promises
retention of external infrastructure nor registers GC roots. Later deleting or
excising an original does not erase these copies. Any authorized erasure must
consider the corpus, exports, previews and backups separately. This Stage 0 package
contains no actual sensitive/excised payload and establishes no global erasure
assurance. Proceeding beyond Stage 0 requires review/authorization.
