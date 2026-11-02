# Explicit installed internal-builtin acceptance

This controller is NOT a default test/fixture launch. Run only in an authorized bounded turn.
[Runtime authority](../../docs/internal-builtins.md), [design/handoff](../../../dml-design/iterations/21-internal-builtins/HANDOFF.md)
and [validation policy](../../docs/validation-policy.md) own scope. No Docker/SSH/Batch/image/service,
new native operation schema or lifetime investigation is used.

Use a **fresh isolated current-source installation** containing new `daggerml.builtin`, linked native
URI support and bundled native CLI. Cached project tools/subprojects suffice; missing tools/downloads
need separate approval. Meson's `python-runtime` tag supplies the installed core/module inventory;
this local route is not wheel/publication or cross-platform assurance. Do not mutate installed20 or
use checkout runtime PYTHONPATH as installed evidence. Preserve compiler/Meson/source/module/native/
CLI identities BEFORE run. Python `-I` isolates the parent; unset BOTH `PYTHONPATH` and
`PYTHONHOME` in the inherited environment so the plain local child also uses the fresh install.

Informative invocation, with the turn's actual fresh Python and new owned output directory:

```sh
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I tests/builtins/installed_story.py run /fresh/owned/story
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I tests/builtins/offline_read.py controls /fresh/owned/story /fresh/owned/story/captured-source.unavailable
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I tests/builtins/offline_read.py read /fresh/owned/story /fresh/owned/story/captured-source.unavailable
```

The sole computational controller creates THREE Q/TWO synchronous LOCAL attempts: nested13+29
returns42/get-v1; source-distinct equal full argument MAP/requested get-v2 reuses OLD T/R42; changed
13+30 remains pending miss then explicitly returns43/get-v2. Construction empty/insert6 + nested
child getters8 + actual postpromotion retained v1/v2 compatibility2 = **16 successful builtin call
positions**, zero support Q/T. Native content dedup does not dedup trace positions or attempts.

Run audit blocks subprocess/connect in metadata/builtin phases. Only `ex.execute_exchange` temporarily
permits the bounded existing local driver; measured Popen tracker admits exactly the expected one
six-argument direct child per invocation. Audit is re-enabled BEFORE observe/receive/public S/native
inspection. Incremental source, request, spawn PID/native pre-dispatch, exit/reaping/completion/native
receipts precede later metadata. An unsuccessful/uncertain child is STOP/no relaunch, not retry.
Only owned original captured-source/workspaces/packets/expected files are renamed unavailable AFTER
known child reaping; original bytes remain inertly retained. SAME pinned all-parent typed/composite
history is imported to fresh replica. Checkout files/old installed20/native19 evidence stay untouched.

`offline_read.py` installs active import/audit blockers BEFORE DML/helpers load and provides separate
actual subprocess/HTTP/urllib-transport/socket controls. Exact stdlib urllib/urllib.parse pure parsing
is allowed; transport is not. It verifies captured helper/controller/runtime/native/CLI hashes and
isolated installed paths, reads SAME stopped replica, recomputes fixed semantics/own-Q-W/S authority
and proves immutable caller+replica data hashes unchanged. It creates NO calls/jobs/records. If a
reader fails, preserve original and correct a nonexecuting reader on SAME history first, never
speculatively rerun computation. Direct computational-controller CLI has only `run`; read helper is
invoked through blocker-FIRST entrypoint.

Current-final readers can explicitly add `--final-manifest /owned/final-manifest.json` after helper
directory. This is a strict two-runtime qualification: ORIGINAL receipt/old installed artifact
hashes remain checked, final inventory must equal original inventory, only declared `builtin.py`
may differ, and every final artifact plus unchanged native/CLI is independently hashed. It does
not overwrite a receipt, skip hash checks or claim original execution used corrected final bytes.
A separate no-job native-backed regression plus SAME-history final read can validate a narrow
pure comparator correction without repeating computation; exact authorization is turn-specific.

[Finite mutations](mutations.py) measure test-private copied source/plugin/controller before a
predicted invariant failure. They are not shipped hooks, exhaustive mutation scores or acceptance
computations. Host test publication substitutions/native fault controls are separate from the sole
installed story. Actual commands/exits/limits and independent review belong to
[Iteration21 results](../../../dml-design/iterations/21-internal-builtins/RESULTS.md).

Development GHA intentionally disabled/NOT RUN, release controls unchanged. Native19 investigation
PAUSED/private candidate incomplete-unexecuted retained; VP-001 OPEN UNKNOWN/no standing waiver.
Local evidence is not platform all-green, a previous shipped builtin-release compatibility test,
security/full-capture/scientific truth or diagnosis of older failures.
