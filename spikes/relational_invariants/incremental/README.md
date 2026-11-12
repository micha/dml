# Isolated incremental controller

Status: bounded isolated prototype **ACCEPTED/COMPLETE/STOPPED**, UNCOMMITTED. See
[results and qualifications](../../../../dml-design/maintenance/relational-testing/INCREMENTAL-RESULTS.md).
Corrected49 focused controls and sole21-request/4E5P6C/6-reuse story pass; SAME native audit853;
ONE complete isolated collection169pass/103.68s. Owning-rule sensitivity outer assertion deliberately
RAWexit1, not a normal check pass. FIRST preparation RAWexit1/order defect preserved in
[failure record](../../../../dml-design/maintenance/relational-testing/INCREMENTAL-PREPARATION-FAILURE.md).
No maintained integration/publication/installed/platform/coverage guarantee. New spike files only;
NOT a maintained DML API, test replacement, installed controller or implementation promotion.
Owning [plan](../../../../dml-design/maintenance/relational-testing/INCREMENTAL-DESIGN.md),
[pre-edit gate](../../../../dml-design/maintenance/relational-testing/INCREMENTAL-PRE-EDIT.md) and
[coordination](../../../../dml-design/maintenance/relational-testing/INCREMENTAL-COORDINATION.md).
User accepted pre-edit and delegated bounded review decisions; original sole story subsequently
passed. Completed permissions do not authorize more commands/reader/engineering by themselves.

## Modules

- `identity.py`: strict canonical dependency envelopes and stage keys; no paths/time/PIDs in keys.
- `artifacts.py`: exact immutable file manifests, partial finalization/admission and bounded sizes.
- `records.py`: NEW ordinary request/attempt/outcome/satisfaction/selection/allocator DAG roles;
  short public storage transactions, own new requests, OLD producer links, separate adoption.
- `stages.py`: fixed map/get exercise, public multi-root import/normalization, SQL-only checking.
  Foreground process receipts and bounded pinned DuckDB children; no arbitrary dispatch.
- `driver.py`: read-only-source snapshot preparation, exact pin checks, fixed stage invocation
  and conditional seven-round story. Fresh completion NEVER automatically adopts a selection.
- `test_*`: pure and tiny native CONTROL metadata/portable seed/admission/provenance controls.
  `conftest.py` is registered explicitly as a plugin because isolated collection uses
  `--noconftest`; its process blocker applies ONLY to NEW incremental control tests, not old tests.

Prepared candidate A copies ALL tracked base bytes plus native artifact; B changes only an owned
comment in builtin.py, so equal behavior does not bypass build invalidation. P2/C2 likewise change
real owned source bytes, not labels. `C-disabled` removes only the owning map-get-value rule for a
later finite sensitivity check; explicit CONTROL profile required, never acceptance adoption.
Frozen as-built native pin + qualified historical build logs are NOT reproducible-build assurance.
No C/codec/storage/API/old roles/tests/thresholds or native19 investigation changed.

## Conditional commands, not automatic activation

From the isolated worktree, with reviewed cached Python/runtime:

```sh
# Stdlib/Git-only source/artifact copying; no native import, stage or compilation:
python -I -B spikes/relational_invariants/incremental/driver.py prepare "$PWD" \
  "$PWD/build/relational-spike/incremental-v1/pins"

# Finite NEW controls, with INCREMENTAL_PINS + cached tool paths set explicitly:
python -m pytest -q --noconftest -p incremental.conftest \
  spikes/relational_invariants/incremental \
  --basetemp=build/relational-spike/incremental-v1/focus-cases \
  --junitxml=build/relational-spike/incremental-v1/focus.xml

# ONLY AFTER explicit pinned-snapshot/readiness acceptance:
python -I -B spikes/relational_invariants/incremental/driver.py story \
  build/relational-spike/incremental-v1/pins/pins.json \
  build/relational-spike/incremental-v1/story
```

Use NEW output directories; no cleanup/replacement of earlier evidence, automatic retry, native
rebuild or dependency acquisition. Logs/exit/admission errors remain raw non-success. Preparation
copies executable bytes, never database/locks. Stage results retain portable bundles/JSONL/closed
DuckDB data; E/P native working stores and C analytical scratch are owned separately, not imported
from historical stores or hidden live handles. Reuse rehashes actual artifact files and verifies
OLD selected producer/key/dependencies; found corruption is error, not a miss/fresh fallback.

This is trusted integration, not a security sandbox. Snapshot files are read-only by convention,
not immutable against their owner. Minimal process environment/library search and loaded library
receipts do not guarantee complete environmental capture; CLI runtime relies on exact binaries/
immutable paths/inherited pinned environment, not post-exit library-map reconstruction. Filesystem
rename and DML publication are not one crash-durable distributed transaction. Fresh-run occurrences
use an explicit actual store namespace plus reserved run/event sequences; stable scenario labels
are comparison labels only. Reused instrumentation is historical, not fresh coverage/platform truth.

No seven-round story, SQL sensitivity, complete spike collection, maintained full gate, GHA,
commit/push, main integration or controller promotion follows a successful focused gate by itself.
