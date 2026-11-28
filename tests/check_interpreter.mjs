// Independent process oracle: never import the replay runner to read ITF or accept verdicts.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const [python, quint, scanner, ...quintArgs] = process.argv.slice(2);
assert(python && quint && scanner, 'expected Python, Quint and the inventory scanner');
assert(quintArgs.length === 0 || (quintArgs.length === 2 && quintArgs[0] === '--quint-script'),
       'expected optional --quint-script <path>');
const quintPrefix = quintArgs.slice(1);
const testFile = (name) => fileURLToPath(new URL(name, import.meta.url));

function run(executable, args, input) {
    const result = spawnSync(executable, args, { encoding: 'utf8', input, timeout: 30_000 });
    if (result.error) throw result.error;
    assert.equal(result.signal, null, `${executable} ${args.join(' ')}`);
    return result;
}

function succeeded(result, label) {
    assert.equal(result.status, 0, `${label}:\n${result.stdout}${result.stderr}`);
}

function quintState(directory, source, field) {
    const output = join(directory, `${basename(source)}.itf.json`);
    const result = run(quint, [...quintPrefix, 'run', source, '--backend=typescript', '--max-samples=1',
                               '--max-steps=0', '--seed=1', '--verbosity=0', `--out-itf=${output}`]);
    succeeded(result, basename(source));
    const trace = JSON.parse(readFileSync(output, 'utf8'), (_key, value) => {
        if (value && typeof value === 'object' && Object.hasOwn(value, '#bigint')) {
            const number = Number(value['#bigint']);
            assert(Number.isSafeInteger(number));
            return number;
        }
        return value;
    });
    assert.equal(trace['#meta']?.status, 'ok');
    assert.deepEqual(trace.vars, [field]);
    assert.equal(trace.states.length, 1);
    assert(Object.hasOwn(trace.states[0], field));
    return trace.states[0][field];
}

function probe(name, request) {
    return run(python, ['-B', testFile(`observe_interpreter_${name}.py`)], JSON.stringify(request));
}

// Plain literals for the small dispatch observer reply, independent of the production encoder.
function literal(value) {
    if (typeof value === 'boolean' || Number.isSafeInteger(value)) return String(value);
    if (typeof value === 'string' && /^[\x20-\x21\x23-\x5b\x5d-\x7e]*$/.test(value)) return JSON.stringify(value);
    if (Array.isArray(value)) return `List(${value.map(literal).join(', ')})`;
    assert(value && typeof value === 'object', 'unsupported dispatch evidence value');
    const fields = Object.entries(value).map(([key, item]) => {
        assert(/^[a-zA-Z][a-zA-Z0-9_]*$/.test(key));
        return `${key}: ${literal(item)}`;
    });
    return `{ ${fields.join(', ')} }`;
}

function loadFixture(directory, name) {
    const source = join(directory, `${name}.qnt`);
    copyFileSync(testFile(`${name}.qnt`), source);
    return quintState(directory, source, 'requests');
}

function dispatch(directory) {
    const requests = loadFixture(directory, 'interpreter_dispatch');
    const result = probe('dispatch', requests);
    succeeded(result, 'dispatch observer');
    const source = join(directory, 'dispatch_replay.qnt');
    writeFileSync(source, `module dispatch_replay {
  import interpreter_dispatch as D from "./interpreter_dispatch"
  pure val observed: D::DispatchEvidence = ${literal(JSON.parse(result.stdout))}
  var failures: List[str]
  action init = failures' = D::dispatchFailures(observed)
  action step = failures' = failures
}\n`);
    assert.deepEqual(quintState(directory, source, 'failures'), [], 'Quint rejected dispatch observations');
    console.log('Quint accepted dispatch, cleanup, scan, binding-error and bundle-parser observations.');
}

function evidenceSource(directory, key, observation, request, comparison) {
    const result = probe('transport', request);
    succeeded(result, `${key} encoder`);
    const { source: evidence, observations } = JSON.parse(result.stdout);
    assert.deepEqual(observations, request.observations, `${key}: encoder mutated its input`);
    assert.equal(typeof evidence, 'string');
    const source = join(directory, `${key}.qnt`);
    writeFileSync(source, `module ${key} {
  import interpreter_transport as T from "./interpreter_transport"
  type Observation = (T::${observation}Observation)
  type Ref = (T::Ref)
  type Attempt = (T::Attempt)
${evidence}
  var passed: bool
  action init = passed' = evidence == T::${comparison}
  action step = passed' = passed
}\n`);
    return source;
}

function transport(directory) {
    const input = loadFixture(directory, 'interpreter_transport');
    for (const [kind, observation, options] of [
        ['batches', 'Batch', {}],
        ['refs', 'Ref', { internRefs: true }],
        ['columns', 'Column', { attemptDefaults: input.defaults }],
    ]) {
        const source = evidenceSource(directory, `transport_${kind}`, observation,
                                      { observations: input[kind], ...options }, kind);
        assert.equal(quintState(directory, source, 'passed'), true, `${kind}: Quint round trip differs`);
    }
    for (const [observations, options, diagnostic] of [
        [input.extraRefField, { internRefs: true }, /exact name and target strings/],
        [input.missingColumn, { attemptDefaults: input.defaults }, /fields do not match evidence defaults/],
        [input.extraColumn, { attemptDefaults: input.defaults }, /fields do not match evidence defaults/],
    ]) {
        const result = probe('transport', { observations, ...options });
        assert.equal(result.status, 1);
        assert.equal(result.stdout, '');
        assert.match(result.stderr, diagnostic);
    }

    // A zero equal to False in Python must not disappear into the bool default.
    const source = evidenceSource(directory, 'transport_wrong_kind', 'Column',
                                  { observations: input.zeroInsteadOfFalse, attemptDefaults: input.defaults },
                                  'columns');
    const result = run(quint, [...quintPrefix, 'typecheck', source]);
    assert.equal(result.status, 1, 'Quint should reject int evidence in a bool column');
    assert.match(result.stdout + result.stderr, /unify (?:int and bool|bool and int)/);
    console.log('Quint reconstructed batched, interned and columnar evidence; malformed inputs were rejected.');
}

function verdicts() {
    const args = ['-B', testFile('run_histories.py'), quint, 'daggerml.core', scanner,
                  testFile('interpreter_verdict_histories.qnt'), testFile('interpreter_verdict.qnt'), ...quintArgs];
    const positive = run(python, args);
    succeeded(positive, 'complete verdict');
    assert.match(positive.stdout, /^history 1: datum_encode\(i64, 42, packed\)=ok\r?$/m);
    assert.match(positive.stdout, /Quint's synthetic rule controls passed/);
    assert.equal(positive.stderr, '');

    const missing = run(python, [...args, '--init', 'missingVerdict']);
    assert.equal(missing.status, 1);
    assert.equal(missing.stdout, '');
    assert.match(missing.stderr, /^trace interpretation failed: history 1: expected one Quint verdict and acceptance flag per step\r?\n?$/);
    console.log('The replay process accepted the complete verdict and rejected the missing verdict.');
}

const directory = mkdtempSync(join(tmpdir(), 'dml-interpreter-'));
try {
    transport(directory);
    verdicts();
    dispatch(directory);
} finally {
    rmSync(directory, { recursive: true, force: true });
}
