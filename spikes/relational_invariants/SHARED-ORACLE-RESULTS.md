# Shared and materialized test-oracle replay

Status: bounded continuation complete, UNCOMMITTED in the isolated worktree. No DML
repository reopened, native reads/builds, source execution, original-test/fixture replay,
new dependency, maintained code change, push/CI or full suite.

## SAME input, same rules

[oracle_replay.py](oracle_replay.py) consumes the44 frozen case datasets from
[selection authority](AUTHORITY-RESULTS.md): decoded facts, scopes including actual packet
inputs, and independently retained original verdicts. It imports no DML modules. The exact
same three SQL rule files are used in all replay paths; SHA256 and every per-case verdict
are retained. All218 scoped verdicts, including65 rejections, agree between replay modes
and with the archived original outcomes; all transition/reuse checks remain clean.

Fact/scope inputs are loaded from retained artifacts, NOT recomputed or reconstructed
as new runtime evidence. Availability refers to each previously collected case's object
set, not current physical repository assurance. No reuse of a historical PID or live handle.

## What is shared

The shared owner admits an immutable raw-fact pool once. Per-key equality and whole-object
decoded-fact fingerprints prevent contradictory descriptions under shared content IDs.
The pool has **4,280 distinct objects**, versus8,154 per-repository object memberships.
Each case still supplies its independent availability set; pooling does not declare objects
physically available in every repository.

Immutable structural projections (field decoding, roles, values, Q/T descriptions,
argument/source relations, operation/trace descriptions, selections, field sets and commit
ancestry) are materialized once. These are NOT cached successful authority verdicts.
Case views filter owner identities; ancestry requires BOTH descendant and ancestor to be
available. Typed missing-edge/root checks separately detect absent case availability even
when the global pool contains the target. Complete supplied object descriptions are checked
against admitted fingerprints when activating a case.

The second variant also materializes selected case-specific target/header/composition/table/
reuse-choice joins AFTER activating the new case. Those rows are refreshed per case; packet
root/fingerprint, headers, intent, binding name, depth and scope remain distinct. SQL still
evaluates eligibility/authority/transition predicates; it does not accept a cached success.

This prototype has ONE sequential oracle owner and mutable active-case views. It does NOT
support concurrent checking of different cases on that shared active state. The earlier
[atomic batch/concurrent snapshot](CONCURRENCY-RESULTS.md) prototype remains separate and
unchanged. A future concurrent integration would need independent case-qualified scopes
or transaction/connection ownership; no daemon/service/framework is implemented here.

## Measured replay results

Finite single-observation comparison on SAME frozen inputs/rules:

| Oracle path | Complete replay seconds |
| --- | ---: |
| Fresh tables/views per case, using the replay bulk loader | **17.373** |
| Shared facts + immutable structural projections | **13.059** |
| Above + refreshed case-scoped materialization | **10.315** |

Shared setup is INCLUDED:1.113s first shared variant;1.046s second. Input artifact reading
was measured separately (about0.14–0.17s), common to the replay inputs. No native extraction
or DML computation occurred in these measurements. Report serialization/disk close are
outside the quoted oracle computation sums.

The second shared variant is about**41% less oracle time** than the isolated replay (~1.68x).
This is NOT a whole-suite/five-minute/statistical/equivalent-full-validator speedup. The
selected SQL assurance is still incomplete relative to original tests. The historical
26.393s authority relational phase had a different loader/admission path and included
native extraction; it is not substituted as the new isolated baseline.

The scoped variant uses the RETAINED isolated44-case measurements/results from the first
replay, not another isolated run. Case names/order and SQL rule digests are checked against
that retained baseline; all actual verdicts are compared again. Frozen input corpus was
not modified. No claim of repeated trials, randomized measurement order or exact warmed/
cold-cache attribution. Shared admission includes consistency checking that the fresh
isolated loader does not need against previous cases; cost subcomponents are not fully
causally isolated.

## Sensitivity controls

[test_oracle_replay.py](test_oracle_replay.py): actual final XML/log **8PASS,8.43s,true exit0**.
One control evaluates all44 cases against their archived verdicts; remaining controls test:

- Switching cases resets availability, scopes and case-materialized state.
- Globally present data cannot silently fill absent case-local availability.
- Ancestry does not borrow a globally present but locally unavailable ancestor.
- Changed immutable object descriptions are rejected, not served from prior cache data.
- Altered packet root or receipt token still rejects after a previously valid case.
- Altered declared intent is not lost through materialized structural projections.

The replay itself also compares shared vs isolated per-case actual verdict dictionaries,
not only aggregate pass counts. No DML import in either replay process.

## Failed tooling probe retained

Initial scoped-materialization control run RAWFAILED:7FAIL/1PASS. All seven failures were
`KeyError: p_compositions`: the fixed-rule-source extractor required a literal space after
`AS`, while the existing SQL uses a newline. The immutable-description rejection control
passed before reaching that missing definition. This was a tool extraction error, not a
DML failure or semantic verdict disagreement.

Corrected SQL-definition whitespace matching and added fail-closed required-definition
checks. Final8 controls pass; original log/XML remain, not relabelled successful. Predicate
SQL files are unchanged. No skip, timeout or assertion weakening.

## Evidence and boundaries

Ignored worktree evidence:

- `build/relational-spike/shared-replay-v1/`: isolated+first shared results and rule hashes.
- `shared-replay-scoped/`: second variant, retained baseline identity, every actual verdict.
- `shared-replay-tests-v1.*`: original failed control run.
- `shared-replay-tests-final.*`: corrected actual8-test evidence.

[scope_schema.py](scope_schema.py) makes scope schema reusable without importing DML;
`paired_runner.py` imports the same definitions. No schema/predicate change is introduced by
that refactor. Existing artifacts remain historical evidence at their original sources.

Completed verdict identity/codec/capture/transfer/budget/custody obligations not yet ported
remain unproved by this optimization. Pooling structural facts does not authorize dropping
original tests or native validation. The next bounded candidate is integration of this
sharing into selected parallel test workloads with explicit per-case identities/lifetimes,
not permission for production/API/cache-framework expansion or native19/VP-001 investigation.
No publication or further run is triggered by this report; work remains isolated.
