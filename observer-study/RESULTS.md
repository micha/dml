# Stage 0 results

## Disposition

**Qualified pass for corpus curation only.** The five handoff scenarios now have a
small frozen evidence package, source hashes/locators, an answer sheet, an explicit
gap inventory and executable integrity checks. No graph convention, model backend,
UI, second producer or production integration was implemented. Human inspection
utility has not yet been evaluated.

The user authorized execution after discussing the handoff and specified
workmux-created tmux windows, interactive Pi, `workmux-notify`, and prompts/steering
through `tmux send-keys`. The coordinator delegated curation and independent review
to two isolated workers, retaining only compact summaries and targeted checks.

## Start here

- [Corpus answer sheet](corpus/ANSWER-SHEET.md): five stories with frozen evidence links.
- [Ground truth](corpus/ground-truth.json): machine-readable cited interpretations.
- [Evidence gaps](corpus/gaps.json): nine explicit limitations, not invented history.
- [Corpus README](corpus/README.md): scope, provenance and validation commands.
- [Initial independent review](review/REPORT.md): original failing probes retained.
- [Independent correction recheck](review/RECHECK.md): qualified-pass disposition.

Curator-authored claims are not independent proof. Original source locators and
full-file hashes remain distinct from normalized fixture identities. This is
retrospective ingestion, not another execution of the historical study.

## Measured delivery

| Measurement | Result | Meaning |
| --- | ---: | --- |
| Selected source snapshots | 23 | Curated reported JSON and safe text/code spans |
| Scenarios / cited facts / gaps | 5 / 17 / 9 | Corpus coverage, interpretations and limitations |
| Selected fixture bytes | 69,976 | Copied selected evidence, not full execution capture |
| Historical checksum bindings | 10 | Equality to reported digests, not authentication |
| Local corpus tests | 39 passed | Validation tests, not research trials |
| Independent adversarial probes | 16 correctly rejected | Malformed synthetic corpus/input cases |
| Producer baseline files | 141 unchanged | Existing nonignored producer files, raw runtime excluded |
| Supporting paths | 6 present at metadata check | 4 regular files and 2 directories; contents not opened |

The coordinator independently reran:

```sh
python3 -B observer-study/corpus/corpus.py --sources --availability
python3 -B observer-study/corpus/test_corpus.py
python3 -B observer-study/review/focused_checks.py
```

All three completed with exit status zero after correction. The checker verified
23 originals and deterministic selected projections. The independent checks
verified 99 selected rows, 78 citation uses and ten historical bindings. These
counts have different units and must not be added into a generic tests-passed total.

Generated records are under ignored `runtime/stage0/`, including
`coordinator-final-validation.json`, `coordinator-final-tests.txt`,
`coordinator-final-focused.json` and `coordinator-final-audit.json`.

## Review and correction history

The initial independent review found no consequential contradiction in the five
scenario mappings, but found four validator defects:

1. Unknown source formats/gap schema and inconsistent ingestion metadata accepted.
2. Duplicate keys and nonfinite values accepted when projecting original JSON.
3. An empty scenario still counted as five-scenario coverage.
4. Original byte lengths and unit types insufficiently checked.

The curator corrected these within the corpus-owned area and added regression
tests. The reviewer independently reran the unchanged original probe script: all
16 reject-required cases now reject, compared with eight unexpected acceptances
initially. The frozen manifest/fixtures/answers/gaps remained unchanged. Initial
findings and failing results were preserved, not overwritten into a success story.

One low-priority, nonblocking observation remains: the optional
`corpus/check_review.py` mirror wrapper trusts the child checker's exit status
rather than independently validating all returned result fields. The actual
unchanged checker was verified directly and passed all probes. Mirror execution
is trusted test code, not a sandbox or live completion verification. See the
[recheck](review/RECHECK.md) for optional hardening and measured boundaries.

## Evidence limitations that need user review

- Adoption preservation and plan-swap outcomes have structured reported evidence,
  but numerical physical-identity/digest receipts and complete victim/survivor IDs
  are absent from the allowed copied evidence. Raw state/logs were not imported.
- Exact reuse counts partly come from inspected model source. Complete recorded
  occurrence traces are unavailable; model cases remain simulations.
- Real disposal-recovery evidence and simulated computation/cleanup progress are
  separate streams, not one invented end-to-end attempt timeline.
- S3 findings remain reported source inspection, not freshly checked primary-source
  copies or cloud experiments.
- No genuine missing/excised dataset was discovered. Missing/unavailable conditions
  are tested synthetically; present supporting paths do not establish content
  integrity or historical completeness.
- Hashes do not authenticate authors, prove independent execution or complete
  closure/environment capture. Copies have their own retention/excision implications.

These are truthful gaps, not validator failures. They limit what later observation
views may claim. No resource retention roots, GC or global erasure assurance exists.

## Preservation and worker completion

The implementation checkout remained clean at `638cc4267d7aca2e34e58c60ba7a54e25f0a20eb`.
The design checkout remains at `0a2a136b7ba44b5591a4852639c50783ee0110a5`; its preexisting
uncommitted study/design work was preserved. All 141 files in the coordinator's
nonignored producer baseline retained their hashes.

Worker reports and atomic completion-marker hashes were checked separately from
notifications. Both interactive Pi processes exited normally with recorded status
zero. Only the two coordinator-created worker windows were closed. Launchers were
frozen before execution. No commits, pushes, study reruns, tool installations,
research cloud operations or raw agent/state/log sweeps were performed.

One coordinator inline verification command had a syntax typo before its Python
body executed; it was corrected and rerun successfully. The corpus checker,
tests and adversarial probes had already completed before that harness error.

## Next decision

Review the answer sheet and decide whether the recorded evidence gaps are adequate
for Stage 1, or whether a separately scoped safe evidence export is needed first.
Stage 1 would explore the narrow model-reader contract, not production DML APIs.
Graph conventions and presentation technology remain open. Work stops here until
further instruction.
