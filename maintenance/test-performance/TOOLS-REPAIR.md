# Project-local validation environment restoration

User authorized investigation/repair by **“sure”** after the explicit request for
project-local tools repair, no global configuration/CI changes.

Status: **restored and verified**; DML clean local15555c0 unchanged, no new runtime
implementation, full suite/build/story/Valgrind execution/CI/commit/push. Separate
[validation-read prototype rejection](VALIDATION-READS-RESULTS.md) remains unchanged.
Environment restoration does not turn rejected prototypes or the five-minute goal green.

## Cause and narrow remedy

`--offline` disables binary-cache substitution. Dependencies were absent from the
local store, so the earlier offline environment preparation attempted source/bootstrap
builds, encountering a fixed-output tinycc source hash mismatch BEFORE pytest.
The [official Nix documentation](https://github.com/NixOS/nix/blob/master/doc/manual/source/release-notes/rl-2.4.md)
confirms offline behavior; [develop profiles](https://github.com/NixOS/nix/blob/master/src/nix/develop.md)
record a build environment, with profile generations serving as GC roots.

Read-only normal-substitution dry run at the SAME pin: THREE small builder/Python-env/
shell derivations, TEN cache paths planned (593.2KiB download/2.7MiB unpacked). Normal
preparation successfully fetched from existing trusted cache.nixos.org, then built the
builder/Python-env/recorded shell. No pin change/source-hash bypass/bootstrap-source
repair/global configuration or additional trust-key/cache endpoint change.

This establishes a successful normal preparation route, NOT why local packages became
absent or the exact historical upstream hash mismatch cause. Garbage collection is a
possible absence mechanism but is NOT evidenced as the historical cause.

## Persistent local state

Original `flake.nix`, `flake.lock`, `mull.nix` exact before/after bytes verified unchanged.
Existing `profile -> profile-1-link` and `mutation-profile -> mutation-profile-2-link`
unchanged. New project-local `validation-profile -> validation-profile-1-link` points to
`/nix/store/2cmisr9y7bqfy80k0s8f13a8l61j4fzb-nix-shell-env`; actual roots/recursive closure
confirm xdist/cov-plugin/psutil/execnet retained. This is a project GC root, NOT a global
profile installation or indefinite retention against explicit root/generation deletion.
Nix roots query also reported removing stale temporary root files (incidental Nix-managed
housekeeping), not global GC or a manual root purge.

New unversioned tools `README.md` records preparation/use/rollback. External tools directory
remains non-Git-versioned; source/docs/profile state evidence retained, not silently committed.

## Actual validation

Evidence: `../dml/build/tools-repair/20261107T234857Z/`:
`before/`, source digests, selected cache settings, dry-run stdout/stderr/exit,
preparation stdout/stderr/exit, smoke XML/log/exit, offline imports/tool versions,
profile roots/closure. All actual commands succeed; original earlier hash failure retained
under holistic representative evidence, not overwritten by this preparation pass.

Prepared Python3.13.15 environment imports:
pytest9.0.3/Hypothesis6.151.10/xdist3.8.0/pytest-cov7.1.0/psutil7.2.2/coverage7.14.1/execnet2.1.2.
Original pinned flake also works offline AFTER normal preparation; GCC/gcov-tool15.3.0,
Valgrind3.26.0/Meson1.10.2/Ninja1.13.2 presence/version verified (not full test execution).

ONE bounded targeted tools smoke using recorded profile:
`test_test_resources.py` + `test_parallel_coverage.py`: TRUEexit0/**46PASS9.02s**;
actual XML46/zero failures/errors/skips. Existing tiny subprocess controls actually test
TWO workers, worker coverage combination, property forwarding/grouping, expected test/
coverage-failure propagation and isolated native counter merge. Tiny C coverage probe
compilation/execution is environment-tool validation, NOT DML native rebuild/native19/
computational-job acceptance. Main native counters and Python coverage database isolated
via invocation environment; no full suite or new runtime performance result claimed.

Verified DML source/index remains clean15555c0/no active pytest/Nix/check owner found.
Development GHA disabled/native19 PAUSED/private candidate retained/VP001 OPEN UNKNOWN/
existing owner/revisit conditions remain. Project repair complete/stopped; later performance
engineering/full gate needs its own concrete bounded plan, not automatic resumption by
restored tools. Both builds/source/evidence coordinator-owned/old coding workers stopped.

Rollback: after verifying same repair-owned paths, remove ONLY new validation profile links
and new tools README if restoration itself is undesired; original tools source/older profiles
require no restoration. Do not remove unrelated roots, edit store objects or launch global GC.
No new design/implementation commit/push requested for this repair; design notes uncommitted.
