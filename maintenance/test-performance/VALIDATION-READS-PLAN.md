# Installed Python validation reads — bounded implementation plan

Outcome: [three measured prototypes rejected](VALIDATION-READS-RESULTS.md), final
implementation restored clean15555c0. Framing below records the initial plan, NOT a
retained reader/as-built cache. Later raw-record edge variants and their rejection
are preserved in results. No full gate or dependency repair occurred.

User's latest “proceed” approves extending optimization to installed Python validation
internals, retaining C/storage/public APIs. First concrete slice: one private bounded
transaction-owned validation reader in `transfer.py`, used by transfer export and builtin
Inspector. No low-level Repository/Transaction implementation or public signature change.

Assurance: cache successful owned immutable raw/decoded reads only, same ACTUAL native
transaction, no refs/writers/failed reads; warm hits still check native validity through an
uncached public ref read (ignored value). No private role codec: reuse installed getter
algorithms/native decoding. Changed HOST getters/codec implementations invalidate/delegate,
unsupported transaction proxies delegate original APIs. Bounds are soft cache limits, never
larger acceptance budgets; transfer and Inspector's cycle/semantic/occurrence/depth/live
limits still run. Inspector retains public `tx` identity; Recorder's value/source/poison
checks remain, metadata writes remain unchanged. No retained-membership or whole semantic
success flags introduced; graph traversal still executes. Cache owned by Inspector/export,
not global, shared across transactions, saved handle or permanent native owner.

Focused work-count/negative tests plus original builtin/transfer/captured controls; SAME
single representative profile before/after (profile counts/instrumentation separate from
suite timing). Only after satisfactory final substantive sources: ONE standard full-v
resource-aware coverage gate when a cached complete tools environment is available. Current
Nix prep remains blocked; no hash repair/dependency fetch authorized. No installation,
acceptance story/native19/CI/push/commit or parallel-worker count/default policy changes.
