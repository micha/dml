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
- [Inspection CLI](spec-next/cli.md): grammar, traversal and presentation.
- [Packaging](packaging-and-distribution.md): shared native builds and installed entry paths.
- [Glossary](spec-next/glossary.md): shared vocabulary.

The [old draft specification](spec/overview.md) describes proposed broader layers;
it is not evidence that those layers are implemented. Design agreements and future
iteration planning live in the sibling
[dml-design checkout](../../dml-design/README.md).
