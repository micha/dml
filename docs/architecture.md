# Architecture

Authority boundary:

- This document is authoritative for the implemented module boundaries and
  navigation to the current sources of truth.
- For normative implemented behavior, see the
  [as-built specification](spec-next/README.md).

The native C core implements datums, literal/sub-DAG-reference nodes, named rooted
DAGs, trees and commits,
with full-record content IDs. LMDB-backed storage transactions persist immutable
objects and atomically create or update repository-scoped refs to commits.
Installed headers separate these module boundaries:

- [error.h](../include/dml/error.h): status and error representation.
- [record.h](../include/dml/record.h): datum codecs, buffers and ID text conversion.
- [object.h](../include/dml/object.h): snapshot/history codecs, borrowed views,
  the ASCII name profile and immutable-object identity.
- [repo.h](../include/dml/repo.h): opaque repository/storage-transaction handles,
  typed object storage, scoped node lookup and ref operations.

xxHash, LMDB, utf8proc and uriparser remain private static dependencies. The root
Meson project links this core into both the inspection CLI and Python extension.
The low-level Python layer supplies owned immutable descriptions and conservative
transaction contexts around opaque native handles; it does not duplicate codecs
or use subprocess test drivers. The Python console entry forwards to the same
native CLI executable bundled in `daggerml`, never PATH's `dml`.

The separately imported `daggerml.local` layer composes only public repository
operations. It closes parent handles before launching a trusted Python child,
pins inputs/binding, and records requests, attempts, publication and final outcomes
as ordinary DAGs/commits/refs. It neither changes native node semantics nor provides
a sandbox. Its owning [contract](spec-next/local-execution.md) explains capture and
interruption limits.

The separately imported `daggerml.transfer` layer also uses only public operations:
validated exact record reads, owned typed descriptions and mutation-guarded packed
insertion. Its [contract](spec-next/transfer.md) owns complete all-parent bundles and
atomic optional-ref import. It neither duplicates codecs nor executes copied source.

The separately imported `daggerml.exchange` composes those public layers for one
pinned step in independent local B. Its [contract](spec-next/repository-execution.md)
owns retained one-shot workspaces, selected-history inspection in private validation
storage and atomic explicit-ref return to A without moving existing heads.
Its additive [asynchronous contract](spec-next/asynchronous-execution.md) separates saved
observation identity/live worker ownership and pins validated P/U/F packets through
coherent public storage reads, without another executor or detached supervision service.
The additive [caller-request contract](spec-next/caller-requests.md) owns Q-only A recording,
public local request builder/imported-Q first registration and exact pinned-Q validation;
exchange never calls private local preparation or manufactures operational reservation refs.

The separately imported `daggerml.ssh` and fixed installed `ssh_worker` transport only
caller-Q jobs over explicit SSH stage/execute/fetch and nonwaiting foreground execute launch.
Saved SSH identity is distinct from live SSHLaunch ownership; fixed nonexecuting observe reuses
public coherent exchange discovery and owning read_observation before packet publication.
Public exchange job reading and unchanged
execute/receive remain authoritative; no private local/transfer/native codec is used.
Its [contract](spec-next/ssh-execution.md) separates local-client reaping from remote lifetime
and recorded scratch cleanup from local Docker acceptance-fixture retirement. No Docker
runtime dependency or native storage entity is added.

The explicitly imported `daggerml.floci` local prototype uses fixed unsigned direct HTTP
for staging/one-shot Batch submission and bounded fresh observations. Its installed job
program owns one public WorkerLaunch and publishes closed complete immutable P/U/F packets
through create-only S3 objects/manifest-last phase slots. No submitting Popen is serialized
or required; service status is diagnostic, not computational outcome. The
[owning contract](spec-next/floci-execution.md) preserves exact-Q/explicit-ref exchange
validation and qualifies service lifetime, acknowledgement loss and ephemeral job-local B.
The internal HTTP family is Floci-specific, not a generic AWS SDK/resource subsystem.
Docker remains explicit local test support; no native entity, packaged controller or runtime
Docker dependency is added.

## Technical navigation

Start with [spec-next/README.md](spec-next/README.md) for the implemented contract:

- [Records and datums](spec-next/records.md): common envelope, identity and ownership.
- [Snapshot and history objects](spec-next/objects.md): fields, names and ordering.
- [Local repository and transactions](spec-next/repository.md): storage, direct
  reference checks, refs and handle lifecycle.
- [Python API](spec-next/python-api.md): conversions, exceptions and native lifetime/context policy.
- [Local recorded Python execution](spec-next/local-execution.md): ordinary execution records,
  cooperative publication, process mechanics and trust/capture limits.
- [Pinned commit transfer](spec-next/transfer.md): bounded exact-record bundles,
  complete typed object closure and atomic import/ref behavior.
- [Execution across local repositories](spec-next/repository-execution.md): explicit
  prepare/execute/receive, selected-history validation and return publication.
- [SSH execution and progress](spec-next/ssh-execution.md): strict endpoint/transport,
  fixed helper, saved identity/foreground owner and exact-Q immutable packet reception.
- [Floci Batch execution](spec-next/floci-execution.md): local fixed HTTP/one-shot
  dispatch, saved external identity, job-side ownership and immutable S3 progress.
- [Inspection CLI](spec-next/cli.md): grammar, traversal and presentation.
- [Packaging](packaging-and-distribution.md): shared native builds and installed entry paths.
- [Glossary](spec-next/glossary.md): shared vocabulary.

The [old draft specification](spec/overview.md) describes proposed broader layers;
it is not evidence that those layers are implemented. Design agreements and future
iteration planning live in the sibling
[dml-design checkout](../../dml-design/README.md).
