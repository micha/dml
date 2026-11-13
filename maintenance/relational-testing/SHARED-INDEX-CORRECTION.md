# Shared indexed contexts — first focused failure / reviewed finite correction

FIRST focus RAW TRUEexit1, **23PASS/1FAIL,0.84s**, actual log/XML in owned `shared-index-v1/`.
Earlier manual static count26 was an arithmetic error; independently counted24 BEFORE execution,
actual24 retained, not a missing-test/fake-pass correction. Failure is in first scoped case SQL
result transport, not native index/context/retention or storage API. Native batch4/24getter positions
already produced; original7 source files archived exact before correction.

Trace: CLI reaches returncode0, stdout begins ANSI-coloured deprecated-lambda warning from existing
invariant SQL, followed by JSON `[]`. `json.loads(stdout)` fails. First CLI PID and FULL raw stdout
were NOT independently retained; pytest traceback contains warning prefix/partial repr and source
flow confirms actual0. No reconstruction claimed. Generic unchanged checker previously executes
view setup separately and doesn't parse that stdout, whereas new one-connection TEMP setup/query
shares stdout. Strict parser correctly refused mixed diagnostics/data; never strip arbitrary
prefixes or suppress warnings. Context7 primary DuckDB docs support COPY query results to JSON;
TEMP/read-only evidence also present in earlier actual connection-local prototype.

Coordinator reviews/approves owning correction within direct user implementation scope:
ONLY new check.py uses `COPY (ordered invariant SELECT) TO ownedfile (FORMAT JSON)`, preserving
read-only pool/TEMP state, existing invariant predicates and capture of actual command/PID/exit/
stdout/stderr. Strict parse NDJSON data file only; missing/malformed result remains failure.
New test_shared.py adds ONE controlled transport regression: warning stays in raw stdout/log,
result file alone determines rows; fake process explicitly a UNIT control, not real CLI evidence.
No old SQL/deadline/threshold/budget/skip/dependency/runtime/native/API edit.

## Transport UNIT harness correction

First narrow UNIT run RAW1/1fail/0.10s, ZERO exercise/SQL. FakeProcess's newly added regex was
overescaped and failed to recognize literal `(FORMAT JSON)` in the generated COPY statement;
traceback/source identify a TEST-only harness defect, not revised checker result. Current two
transport source files preserved under transport-failed-source BEFORE repair. Coordinator approves
ONLY test regex/literal-ANSI fixture correction and ONE additional UNIT run on repaired source,
then still-unconsumed SAME4query pass. No whole-focus/dataset repeat or warning suppression.
Both raw failures retained; no source relaxation or platform/native attribution implied.

Finite continuation: ONE corrected four-case query pass on SAME retained normalized facts/catalog/
closed pool (ZERO new exercise/native import/normalization), one narrow new transport control,
then source/readiness review before ONE bounded standalone4case demo/portable transfer and ONE
complete isolated collection. No second whole focus or failed batch replacement, automatic
repeat-until-green or production/old-runtime investigation. Any new failure gets primary evidence/
causal plan before further activation. Old raw failure remains failed after later passes.
