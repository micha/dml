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

from apply_input import SealedPlan, SealUnavailable, sealed_plan
from fixture_language import InvalidFixture, fixture, load, plan_configuration

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

def cli(root, *args, pass_fds=()):
    # No inherited TF_VAR/TF_CLI_ARGS/credential environment. Built-in only.
    root = Path(root).resolve()
    env = {'PATH': os.environ['PATH'], 'HOME': str(root), 'CHECKPOINT_DISABLE': '1',
           'TF_IN_AUTOMATION': '1'}
    p = subprocess.run([verified_tool(), *args], cwd=root, env=env,
                       capture_output=True, text=True, timeout=60,
                       pass_fds=pass_fds, umask=0o077)
    # Never persist stdout/stderr, including state pull/show/output JSON. No secret
    # detection heuristic: controlled inputs can still be sensitive to their owner.
    fd = os.open(root / 'cli.log', os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'a') as f:
        os.fchmod(f.fileno(),0o600)
        f.write(json.dumps({'argv':args, 'code':p.returncode, 'pass_fds':pass_fds,
                            'stdout_length':len(p.stdout), 'stderr_length':len(p.stderr),
                            'output_logging':'omitted'}) + '\n')
    need(p.returncode == 0, f'CLI failed (output restricted): {args}; code={p.returncode}')
    return p.stdout

def material(root):
    # Read each captured file once; parse/hash the same bytes. Not full HCL capture.
    files = sorted(p for p in root.iterdir() if p.name.endswith(('.tf', '.tf.json', '.tfvars', '.tfvars.json')) or p.name == '.terraform.lock.hcl')
    need(all(not p.is_symlink() for p in files), 'symlink material')
    need({p.name for p in files} <= {'main.tf.json', 'inputs.auto.tfvars.json'}, 'unsupported material')
    need((root / 'main.tf.json').is_file(), 'missing material')
    data = {p.name:p.read_bytes() for p in files}
    try:
        fixture(load(data['main.tf.json']), load(data.get('inputs.auto.tfvars.json',b'{}')))
    except InvalidFixture as e:
        raise Rejected(str(e)) from e
    return digest(canonical({name:digest(value) for name,value in data.items()}))

@contextlib.contextmanager
def approved_plan(path, expected_digest=None):
    try:
        with sealed_plan(path, expected_digest) as snapshot:
            yield snapshot
    except SealUnavailable as e:
        raise Rejected(str(e)) from e


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

def plan_census(doc, receipt):
    module = doc.get('configuration', {}).get('root_module', {})
    try:
        configured = plan_configuration(module, doc.get('variables',{}))
    except InvalidFixture as e:
        raise Rejected(str(e)) from e
    after = set(receipt['manifest'])
    seen = set()
    for change in doc.get('resource_changes', []):
        address = change['address']
        need(address not in seen, 'duplicate plan resource census')
        seen.add(address)
        actions = change['change']['actions']
        if actions == ['delete']:
            need(address in after, 'unobserved deletion')
            after.remove(address)
        else:
            need(address in configured, 'unconfigured planned resource')
            if actions == ['create']:
                need(address not in after, 'identity collision in creation')
                after.add(address)
            else:
                need(address in after, 'unobserved planned resource')
    planned_root = doc.get('planned_values',{}).get('root_module',{})
    need(not planned_root.get('child_modules'), 'unsupported planned modules')
    planned = {}
    for r in planned_root.get('resources',[]):
        need(r.get('mode') == 'managed' and r.get('type') == 'terraform_data'
             and r.get('provider_name') == 'terraform.io/builtin/terraform'
             and 'index' not in r and r['address'] not in planned, 'unsupported planned census')
        planned[r['address']] = r.get('values',{}).get('id')
    need(set(planned) == after, 'incomplete planned resource census')
    output = doc.get('output_changes',{}).get('dml_manifest')
    need(isinstance(output,dict) and not output.get('after_sensitive',False), 'missing/nonpublic planned census')
    known = output.get('after')
    unknown = output.get('after_unknown',False)
    if not after and known is None:
        need(unknown is False, 'unknown empty planned census')
    else:
        need(isinstance(known,dict) and (unknown is False or isinstance(unknown,dict)), 'malformed planned census')
        unknown = {} if unknown is False else unknown
        need(set(known).isdisjoint(unknown) and set(known) | set(unknown) == after, 'incomplete planned manifest census')
        need(all(value == planned[address] and isinstance(value,str) for address,value in known.items()), 'planned identity mismatch')
        need(all(value is True and planned[address] is None for address,value in unknown.items()), 'unknown planned identity mismatch')
    return {'before':sorted(receipt['manifest']), 'after':sorted(after)}

class Gate:
    def __init__(self, root, journal):
        self.root, self.journal = Path(root).resolve(), journal
    def plan(self, filename='cleanup.tfplan', *options):
        before_material = material(self.root)
        before = observe(self.root)
        cli(self.root, 'plan', '-input=false', '-no-color', '-out=' + filename, *options)
        need(material(self.root) == before_material and observe(self.root) == before, 'changed during plan')
        with approved_plan(self.root / filename) as snapshot:
            doc = json.loads(cli(self.root, 'show', '-json', snapshot.path, pass_fds=snapshot.pass_fds))
            victims = plan_victims(doc, before)
            census = plan_census(doc, before)
            plan_digest = snapshot.sha256
        with self.journal.tx() as c:
            revision = self.journal.revision(c)
        return {'plan_digest':plan_digest, 'material_digest':before_material, 'census':census,
                'receipt':before, 'victims':victims, 'root_revision':revision}
    def check(self, ticket, plan):
        if not isinstance(plan, SealedPlan):
            with approved_plan(plan,ticket['plan_digest']) as snapshot:
                return self.check(ticket,snapshot)
        need(plan.sha256 == ticket['plan_digest'], 'changed plan bytes')
        need(material(self.root) == ticket['material_digest'], 'stale configuration/input')
        need(observe(self.root) == ticket['receipt'], 'stale manager receipt')
        doc = json.loads(cli(self.root, 'show', '-json', plan.path, pass_fds=plan.pass_fds))
        victims = plan_victims(doc, ticket['receipt'])
        need(victims == ticket['victims'], 'ticket victim/plan mismatch')
        need(plan_census(doc,ticket['receipt']) == ticket.get('census'), 'ticket census/plan mismatch')
    def apply(self, ticket, token, plan, before_effect=None, after_effect=None):
        # One source read: the SAME sealed object is checked and passed to apply.
        with approved_plan(plan,ticket['plan_digest']) as snapshot:
            with self.journal.tx() as c:
                row = c.execute('SELECT ticket,status FROM reservations WHERE token=?', (token,)).fetchone()
                need(row is not None and row[1] == 'reserved' and json.loads(row[0]) == ticket, 'missing/mismatched/live reservation')
                self.journal.validate(c, ticket)
                self.check(ticket, snapshot)
                c.execute("UPDATE reservations SET status='unknown',outcome='apply may not have started' WHERE token=?", (token,))
            with self.journal.tx() as c:
                # Local writer lock ONLY excludes cooperative journal publishers.
                self.journal.validate(c, ticket)
                self.check(ticket, snapshot)
                if before_effect:
                    before_effect()
                # Catch deterministic configuration changes at this test barrier;
                # not an atomic defense against hostile concurrent file writers.
                need(material(self.root) == ticket['material_digest'], 'stale configuration/input at effect boundary')
                cli(self.root, 'apply', '-input=false', '-no-color', snapshot.path, pass_fds=snapshot.pass_fds)
                if after_effect:
                    after_effect()
                after = observe(self.root)
                need(sorted(after['manifest']) == ticket['census']['after'], 'post-effect census mismatch')
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
        print(json.dumps(g.apply(json.loads(a.ticket.read_text()), a.token, g.root/a.plan)))
