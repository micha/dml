# Epic: Remote push and fetch

**Status: In progress.** This is a work plan, not an API or implementation
contract. The push-side C primitives are implemented; the tracking ref,
filesystem workflow, and network transport are not. See the [as-built transfer
contract](../spec-next/transfer.md) and the [historical remotes draft](../spec/remotes.md).

## Goal

Exchange a named DML snapshot between two repositories. Push publishes to a
selected remote ref without overwriting divergent history. Fetch records the
observed remote tip in a local tracking ref without moving a local head. Either
receiver can reopen its repository and read the snapshot and its full history
without access to the sender.

## First slice: one ref, two filesystem repositories

Start with two initialized repositories on the local filesystem. Reuse the
existing self-contained commit bundle and its limits; no object negotiation or
new wire format. First build the push-side primitives: export by ref and
conditional import and publication in one destination write transaction.

- **Both directions:** Resolve the selected source ref and export the exact
  commit from one read snapshot. The operation transfers that snapshot even if
  the source ref later moves. Compare the destination ref against an expected
  tip or expected absence. Validate and import the bundle and publish the ref
  together; a rejected operation leaves no new objects or ref changes of its own.
- **Push:** Create an absent destination ref or accept the same tip or a
  fast-forward. A fast-forward means the previous tip is reachable through any
  chain of commit parents, not just first parents. A dangling destination ref
  is not an absent ref. A valid same-tip push with a matching expectation is a
  no-op; it does not bypass the expectation check.
- **Fetch:** Update only the tracking ref for the selected remote and ref. If
  the source ref is missing, report that without deleting local state. The
  tracking-ref layout and whether fetch accepts remote rewinds are open.

The receiving DML core owns repository checks and publication. Transport moves
requests and bundles; it does not decide ancestry or hold a repository write
transaction open across network I/O. A bundle's content IDs do not authenticate
its sender or transfer resources referenced by URI.

## Delivery and evidence

1. **Model conditional receive.** Use [Quint/TLC](../validation-policy.md#design-with-tlc-validate-implementation-with-replay)
   to model source selection, competing writers, rejected updates, and collection
   around the publication boundary. Include two divergent pushes with the same
   expected tip: at most one publishes, and the loser leaves no new objects.
2. **Prove the filesystem round trip.** Replay the atomic receive in core tests
   and push/fetch in a separate workflow test. Cover create, fast-forward through
   a non-first parent, same tip, divergence, stale expectations in both
   directions, malformed bundles, and missing source refs. Reopen repositories
   to verify rollback, unchanged local heads after fetch, and retention through
   garbage collection.
3. **Carry the same operations over one authenticated network transport.** Pick
   the transport and deployment model after the filesystem slice. Test an
   interrupted transfer and a lost reply after publication separately. A lost
   reply makes the outcome unknown; reading the current tip can confirm its
   current value, not whether that particular push committed.

## Design evidence

The [Quint model](../../spec/remote_push_fetch_design.qnt) bounds the problem
to two clients, one destination slot, a separate local head, and a four-commit
source graph with divergent children and a two-parent descendant. It models
fetch as compare-and-swap without an ancestry restriction, so a remote rewind
can be recorded. This is a design candidate, not an implemented fetch rule. It
assumes clean storage and atomic transactions; malformed bundles and failed
commits are abstract rejection cases, not byte-level or native fault checks.

With Java on `PATH` and Quint 0.34.0, run separately from CI:

```sh
mkdir -p build/remote-push-fetch-tlc
(cd build/remote-push-fetch-tlc && quint verify ../../spec/remote_push_fetch_design.qnt \
  --backend=tlc --invariants decision atomicPublish noResidue exactExport snapshotsAndRetention exclusiveDivergentPush \
  --search-observations)
```

TLC found no violation of the six invariants and reached all 14 observations,
including an otherwise-eligible stale push, a divergent race loser, a
second-parent fast-forward, and publication after the source ref moves and its
old closure is collected. Removing the destination comparison or substituting a
valid but unselected source tip each produced a counterexample. The model checks
safety, not liveness.

Out of scope for this epic: pull/merge, force push, pruning and ref deletion,
atomic multi-ref updates, incremental transfer, and remote execution.
