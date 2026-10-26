#!/usr/bin/env python3
"""Candidate admission for a deliberately narrow non-secret terraform_data lab.
The local journal is a FAKE research journal, not DML or the journal worker API.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
TOFU = HERE.parent / 'tools/tofu'
ARCHIVE = HERE.parent / 'tools/tofu_1.13.2_linux_amd64.zip'
SHA = '723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5'

class Rejected(RuntimeError):
    pass

def need(ok, message):
    if not ok:
        raise Rejected(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def verified_tool():
    need(digest(ARCHIVE.read_bytes()) == SHA, 'archive checksum')
    with zipfile.ZipFile(ARCHIVE) as z:
        need(digest(TOFU.read_bytes()) == digest(z.read('tofu')), 'binary checksum')
    return str(TOFU)

def cli(root, *args):
    # No inherited TF_VAR/TF_CLI_ARGS/credential environment. Built-in only.
    env = {'PATH': os.environ['PATH'], 'HOME': str(root), 'CHECKPOINT_DISABLE': '1',
           'TF_IN_AUTOMATION': '1'}
    p = subprocess.run([verified_tool(), *args], cwd=root, env=env,
                       capture_output=True, text=True, timeout=60)
    with (root / 'cli.log').open('a') as f:
        f.write(json.dumps({'argv':args, 'code':p.returncode, 'stdout':p.stdout,
                            'stderr':p.stderr}) + '\n')
    need(p.returncode == 0, f'CLI failed: {args}: {p.stderr}')
    return p.stdout

def material(root):
    # A deliberately restricted captured input bundle, not a universal HCL parser.
    files = sorted(p for p in root.iterdir() if p.name.endswith(('.tf', '.tf.json', '.tfvars', '.tfvars.json')) or p.name == '.terraform.lock.hcl')
    need(all(not p.is_symlink() for p in files), 'symlink material')
    need({p.name for p in files} <= {'main.tf.json', 'inputs.auto.tfvars.json'}, 'unsupported material')
    need((root / 'main.tf.json').is_file(), 'missing material')
    config = json.loads((root / 'main.tf.json').read_text())
    need(set(config) <= {'resource', 'output', 'variable'}, 'unsupported configuration')
    need(set(config.get('resource', {})) <= {'terraform_data'}, 'unsupported resource')
    for name, spec in config.get('resource', {}).get('terraform_data', {}).items():
        need(name.isidentifier() and set(spec) <= {'input', 'triggers_replace', 'lifecycle'}, 'unsupported resource effects')
        need(set(spec.get('lifecycle', {})) <= {'prevent_destroy'}, 'unsupported lifecycle')
    need(set(config.get('output', {})) <= {'dml_manifest'}, 'unsupported output')
    need(not config.get('output', {}).get('dml_manifest', {}).get('sensitive', False), 'secret manifest')
    # Variable validations/functions and external inputs are outside this experiment.
    for spec in config.get('variable', {}).values():
        need(set(spec) <= {'type', 'default', 'sensitive'} and not spec.get('sensitive', False), 'unsupported variable')
    return digest(canonical({p.name:digest(p.read_bytes()) for p in files}))

def receipt_from_state(state):
    need(state.get('version') == 4 and isinstance(state.get('lineage'), str)
         and type(state.get('serial')) is int, 'unknown state')
    out = state.get('outputs', {}).get('dml_manifest')
    need(out is not None and not out.get('sensitive', False), 'missing/nonpublic receipt')
    manifest = out.get('value')
    need(isinstance(manifest, dict), 'malformed manifest')
    ids = {}
    for r in state.get('resources', []):
        need(r.get('mode') == 'managed' and r.get('type') == 'terraform_data'
             and not r.get('module') and r.get('provider') == 'provider["terraform.io/builtin/terraform"]', 'unsupported state resource')
        instances = r.get('instances', [])
        need(len(instances) == 1 and 'index_key' not in instances[0]
             and 'deposed' not in instances[0], 'unsupported instance')
        ident = instances[0].get('attributes', {}).get('id')
        need(isinstance(ident, str) and bool(ident), 'unknown identity')
        ids['terraform_data.' + r['name']] = ident
    need(manifest == ids and len(set(ids.values())) == len(ids), 'malformed identity mapping')
    return {'lineage':state['lineage'], 'serial':state['serial'], 'manifest':manifest,
            'snapshot_digest':digest(canonical(state))}

def observe(root):
    # Only this projection leaves the manager boundary; full state is not exported.
    return receipt_from_state(json.loads(cli(root, 'state', 'pull')))

class FakeJournal:
    """Durable local fake. Membership and roots are manual test fixtures."""
    def __init__(self, path):
        self.path = str(path)
        with self.tx() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER);
            INSERT OR IGNORE INTO meta VALUES ('revision',0);
            CREATE TABLE IF NOT EXISTS retained (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS disposition (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS members (name TEXT PRIMARY KEY, available INTEGER);
            CREATE TABLE IF NOT EXISTS reservations (token TEXT PRIMARY KEY, ticket TEXT, status TEXT, outcome TEXT);''')
    @contextlib.contextmanager
    def tx(self):
        c = sqlite3.connect(self.path, timeout=5)
        c.execute('PRAGMA synchronous=FULL')
        c.execute('BEGIN IMMEDIATE')
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()
    def revision(self, c):
        return c.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0]
    def publish(self, ident=None, member=None, disposition=None):
        with self.tx() as c:
            # Conservative manager-wide fence: publication does not race apply.
            need(not c.execute("SELECT 1 FROM reservations WHERE status IN ('reserved','unknown')").fetchone(), 'live/unknown reservation')
            if ident:
                c.execute('INSERT OR IGNORE INTO retained VALUES (?)', (ident,))
            if member:
                c.execute('INSERT OR REPLACE INTO members VALUES (?,1)', (member,))
            if disposition:
                c.execute('INSERT OR IGNORE INTO disposition VALUES (?)', (disposition,))
            c.execute("UPDATE meta SET value=value+1 WHERE key='revision'")
    def validate(self, c, ticket):
        need(ticket['root_revision'] == self.revision(c), 'stale root/membership revision')
        need(not c.execute('SELECT 1 FROM members WHERE available=0').fetchone(), 'unavailable member')
        for ident in ticket['victims'].values():
            retained = c.execute('SELECT 1 FROM retained WHERE id=?', (ident,)).fetchone()
            authorized = c.execute('SELECT 1 FROM disposition WHERE id=?', (ident,)).fetchone()
            need(not retained or authorized, 'retained actual identity')
    def reserve(self, ticket):
        with self.tx() as c:
            self.validate(c, ticket)
            need(not c.execute("SELECT 1 FROM reservations WHERE status IN ('reserved','unknown')").fetchone(), 'live/unknown reservation')
            token = str(uuid.uuid4())
            c.execute('INSERT INTO reservations VALUES (?,?,?,?)', (token,json.dumps(ticket),'reserved',None))
        return token

def plan_victims(doc, receipt):
    need(doc.get('format_version') == '1.2' and doc.get('errored', False) is False, 'unsupported plan format')
    module = doc.get('configuration', {}).get('root_module', {})
    need(not module.get('module_calls'), 'unsupported plan modules')
    for resource in module.get('resources', []):
        need(not resource.get('provisioners') and resource.get('type') == 'terraform_data', 'unsupported plan effects')
    victims = {}
    for change in doc.get('resource_changes', []):
        need(change.get('type') == 'terraform_data' and change.get('mode') == 'managed'
             and not change.get('module_address') and 'index' not in change
             and 'importing' not in change.get('change', {}), 'unsupported plan resource')
        actions = change['change']['actions']
        need(actions in [['no-op'], ['create'], ['update'], ['delete'], ['delete','create'], ['create','delete']], 'unsupported actions')
        if 'update' in actions or 'delete' in actions:
            address = change['address']
            ident = change['change'].get('before', {}).get('id')
            need(ident is not None and receipt['manifest'].get(address) == ident, 'plan/receipt identity mismatch')
            victims[address] = ident
    return victims

class Gate:
    def __init__(self, root, journal):
        self.root, self.journal = Path(root), journal
    def plan(self, filename='cleanup.tfplan', *options):
        before_material = material(self.root)
        before = observe(self.root)
        cli(self.root, 'plan', '-input=false', '-no-color', '-out=' + filename, *options)
        need(material(self.root) == before_material and observe(self.root) == before, 'changed during plan')
        plan = self.root / filename
        doc = json.loads(cli(self.root, 'show', '-json', str(plan)))
        victims = plan_victims(doc, before)
        with self.journal.tx() as c:
            revision = self.journal.revision(c)
        ticket = {'plan_digest':digest(plan.read_bytes()), 'material_digest':before_material,
                  'receipt':before, 'victims':victims, 'root_revision':revision}
        return ticket
    def check(self, ticket, plan):
        need(digest(Path(plan).read_bytes()) == ticket['plan_digest'], 'changed plan bytes')
        need(material(self.root) == ticket['material_digest'], 'stale configuration/input')
        need(observe(self.root) == ticket['receipt'], 'stale manager receipt')
        doc = json.loads(cli(self.root, 'show', '-json', str(plan)))
        victims = plan_victims(doc, ticket['receipt'])
        need(victims == ticket['victims'], 'ticket victim/plan mismatch')
    def apply(self, ticket, token, plan, before_effect=None, after_effect=None):
        with self.journal.tx() as c:
            row = c.execute('SELECT ticket,status FROM reservations WHERE token=?', (token,)).fetchone()
            need(row is not None and row[1] == 'reserved' and json.loads(row[0]) == ticket, 'missing/mismatched/live reservation')
            self.journal.validate(c, ticket)
            self.check(ticket, plan)
            # Commit unknown before invoking any side effect. A kill leaves durable uncertainty.
            c.execute("UPDATE reservations SET status='unknown',outcome='apply may not have started' WHERE token=?", (token,))
        with self.journal.tx() as c:
            # Holding a local writer transaction across subprocess works ONLY cooperatively.
            self.journal.validate(c, ticket)
            self.check(ticket, plan)
            if before_effect:
                before_effect()
            try:
                cli(self.root, 'apply', '-input=false', '-no-color', str(plan))
                if after_effect:
                    after_effect()
                after = observe(self.root)
            except BaseException:
                # Rollback keeps the already committed unknown. No automatic release.
                raise
            c.execute("UPDATE reservations SET status='completed',outcome=? WHERE token=?", (json.dumps(after),token))
        return after

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan','reserve','apply','observe'])
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--journal', required=True, type=Path)
    p.add_argument('--ticket', type=Path)
    p.add_argument('--plan', default='cleanup.tfplan')
    p.add_argument('--destroy', action='store_true')
    p.add_argument('--token')
    a = p.parse_args()
    j = FakeJournal(a.journal)
    g = Gate(a.root, j)
    if a.action == 'observe':
        print(json.dumps(observe(a.root)))
    elif a.action == 'plan':
        t = g.plan(a.plan, *(['-destroy'] if a.destroy else []))
        a.ticket.write_text(json.dumps(t, indent=2)+'\n')
    elif a.action == 'reserve':
        print(j.reserve(json.loads(a.ticket.read_text())))
    else:
        print(json.dumps(g.apply(json.loads(a.ticket.read_text()), a.token, a.root/a.plan)))
