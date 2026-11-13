# Incremental prototype — accepted pre-edit continuation / finite focused gate

User **“accepted. proceed.”** accepts [pre-edit](INCREMENTAL-PRE-EDIT.md). Current assistant
implements ONLY new isolated spike files; no separate agent or main/Iteration25 source/build use.
This permits draft implementation/snapshot preparation/ONE finite focused invocation, not the
seven-round story or final complete spike collection before readiness. No commit/push/install/build.

## Draft scope and static evidence before focus

Twelve NEW files under `../dml-relational-spike/spikes/relational_invariants/incremental/`:
`__init__.py`, `identity.py`, `artifacts.py`, `records.py`, `stages.py`, `driver.py`, `conftest.py`,
`test_identity.py`, `test_artifacts.py`, `test_records.py`, `test_evidence.py`, `README.md`.
Existing spike/native/maintained source remains unchanged; Git tracked diff empty at15555c0.
AST parse/EOF/trailing-whitespace checks pass all11 Python/new12 files. This is static, not runtime.

Draft has fixed map/get E, public multi-root P and SQL C wrappers, exact pin/source comparison,
process/import receipts, artifact manifests/known selectors/cycle-free ordinary records,
explicit actual store namespace + reserved run/event sequences and separate adoption. CLI provides
`prepare` and conditional `story`; no actor triggered on import/preparation. Sensitivity C payload
requires CONTROL profile; candidate B and P2/C2 are real comment-byte edits in owned copies.

Narrow fixture-registration refinement: isolated `--noconftest` also disables our NEW conftest.
Explicit `-p incremental.conftest` registration is required; its autouse process/network blocker
checks test ownership and applies ONLY to NEW incremental controls, not original spike tests.
No original fixture/assertion modification/skip/threshold change. This was found statically,
not a hidden failed collection or suite run. Final isolated collection will need this plugin
and INCREMENTAL_PINS too; maintained standard gate unchanged/not run.

## Exact finite focus

Static expected parameterized cases **48**:

| Source | Cases | Foundation/behavior |
| --- | ---: | --- |
| test_identity.py | 28 | All15 dependency mutations,3 context/namespace/limit mutations,6 ambiguous values, duplicates/unknown inputs, relative manifest/path/symlink/conflict, actual A/B/P2/C2 code partition, E actual-variant guard |
| test_artifacts.py | 8 |6 missing/tamper/unlisted/symlink/manifest/partial faults; before-finalize change; exact status/exit/profile/admission |
| test_records.py | 10 | Explicit NEW Q/OLD T satisfaction, no automatic adoption, old/sibling branches,2 failed/rejected+unknown, stale basis/duplicate completion,4 invalid selectors, wrong producer/unrelated selector, allocator/fork/gap |
| test_evidence.py | 2 |ONE simple literal42/DAG/tree/commit portable seed/import/root rejection/ref rollback; static actual comment variants and owning-rule removal |

ONE session CONTROL store shared by native metadata controls; ONE simple portable seed exported
from it, imported to one separate owned store. No real map/get call, E/P/C stage invocation,
OS child, DuckDB query, historical native store replay, compilation or provisioning in focus.
Dummy CONTROL artifact data explicitly says NOT stage execution, computational namespace/context
cannot satisfy real acceptance stage keys. Ownership remains short native scopes; no live handles
retained. Failed controls STOP for reviewed causal response; no automatic second invocation.

Prepare NEW `build/relational-spike/incremental-v1/pins` via stdlib/Git-only driver. Retain exact
snapshot assets/package/core/runtime/key manifests and raw prepare stdout/stderr/true exit.
No DML/native import/CLI stage activation in preparation; existing Nix closure query is read-only.

Focused command from isolated worktree (with exact existing tool/native runtime pins):

```sh
python -m pytest -q --noconftest -p incremental.conftest \
  spikes/relational_invariants/incremental \
  --basetemp=build/relational-spike/incremental-v1/focus-cases \
  --junitxml=build/relational-spike/incremental-v1/focus.xml
```

Explicit process-only environment: pinned Python/glibc/GCC, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONDONTWRITEBYTECODE=1, INCREMENTAL_PINS=frozen receipt; PYTHONPATH contains owned spike path
and existing `/nix/store/qx9y6qslvc3pw8mblqx77cm1viv2dyzq-python3-3.13.15-env/lib/python3.13/site-packages`.
No dependency acquisition. Current read-only listing of that cached environment includes pytest9.0.3/
Hypothesis6.151.10 plus other pre-existing packages; package presence is NOT a new install or older
missing-package diagnosis. New focus does not need DuckDB Python binding or DML_BIN; those remain
required only for proposed later complete original spike collection. Request exact logs/XML/true exit,
not a bash cutoff; no repeated gate for timing/coverage. Planned48 is not an actual pass/count.

## Stop

Freeze/preserve focused outcome/source/pins for readiness review. Seven-round E/P/C story, SQL
sensitivity, complete spike collection, maintained full gate/GHA/main integration/controller
promotion/publication remain unrun and gated. GHA disabled/native19 PAUSED/private candidate retained/
VP001 OPEN UNKNOWN/Iteration25 authority unchanged. No older diagnosis, new platform/coverage100
or security/reproducibility guarantee follows this metadata proof.
