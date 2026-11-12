"""Pure catalog/context projection over ONE generic native extraction, not per-case reads."""

from collections import defaultdict
import json
from pathlib import Path

from incremental.identity import canonical, exact, parse
from normalizer import extract
from schema import SCHEMA
from .exercise import CONTEXT, DESCRIPTION, INDEX, LIMITS, OBSERVATIONS, OCCURRENCE, RUN, validate_cases


class Facts:
    def __init__(self, rows):
        self.rows = rows
        self.objects = {(r['kind'], r['oid']) for r in rows['objects']}
        if len(self.objects) != len(rows['objects']):
            raise ValueError('duplicate typed object description')
        self.commits = {r['oid']: r for r in rows['commits']}
        self.dags = {r['oid']: r for r in rows['dags']}
        self.nodes = {r['oid']: r for r in rows['nodes']}
        self.datums = {r['oid']: r for r in rows['datums']}
        self.fields, self.trees, self.children = defaultdict(dict), defaultdict(dict), defaultdict(list)
        for r in rows['fields']:
            if r['name'] in self.fields[r['dag']]:
                raise ValueError('duplicate DAG field')
            self.fields[r['dag']][r['name']] = r['node']
        for r in rows['tree_entries']:
            if r['name'] in self.trees[r['oid']]:
                raise ValueError('duplicate tree field')
            self.trees[r['oid']][r['name']] = r['dag']
        for r in rows['edges']:
            self.children[r['src_kind'], r['src']].append(r)

    def parents(self, commit):
        if ('commit', commit) not in self.objects:
            raise ValueError('missing indexed commit')
        edges = [r for r in self.children['commit', commit] if r['label'].startswith('parent-')]
        edges.sort(key=lambda r: int(r['label'].split('-')[1]))
        if [r['label'] for r in edges] != [f'parent-{i}' for i in range(len(edges))]:
            raise ValueError('parent positions differ')
        return [r['dst'] for r in edges]

    def tree(self, commit):
        self.parents(commit)
        return self.trees[self.commits[commit]['tree_id']]

    def field(self, dag, name, kind):
        node = self.nodes[self.fields[dag][name]]
        if kind == 'subdag':
            if node['kind'] != 'subdag' or ('dag', node['target']) not in self.objects:
                raise ValueError('expected available SubDAG link')
            return node['target']
        if node['kind'] != 'literal':
            raise ValueError('expected literal field')
        datum = self.datums[node['target']]
        if datum['kind'] != kind:
            raise ValueError('field native datum kind differs')
        value = datum['scalar']
        if kind == 'bytes':
            return bytes.fromhex(value)
        if kind == 'i64':
            return int(value)
        if kind == 'null':
            return None
        return value

    def identity(self, dag, name):
        value = self.field(dag, name, 'bytes')
        if len(value) != 16:
            raise ValueError('expected 16-byte immutable ID')
        return value.hex()

    def ids(self, dag, name):
        node = self.nodes[self.fields[dag][name]]
        if node['kind'] != 'literal' or self.datums[node['target']]['kind'] != 'list':
            raise ValueError('expected literal LIST of IDs')
        children = sorted(self.children['datum', node['target']], key=lambda r: int(r['label'].split('-')[1]))
        if [r['label'] for r in children] != [f'item-{i}' for i in range(len(children))]:
            raise ValueError('LIST positions differ')
        result = []
        for edge in children:
            datum = self.datums[edge['dst']]
            if datum['kind'] != 'bytes' or len(bytes.fromhex(datum['scalar'])) != 16:
                raise ValueError('LIST child ID kind/size differs')
            result.append(datum['scalar'])
        return result

    def shape(self, dag, role, fields):
        exact(dict(self.fields[dag]), {'role', *fields})
        if self.dags[dag]['root'] != self.fields[dag]['role'] or self.field(dag, 'role', 'string') != role:
            raise ValueError('profile role/root differs')

    def index(self, publication):
        tree = self.tree(publication)
        exact(dict(tree), {'exercise-index', 'exercise-run'})
        dag = tree['exercise-index']
        names = sorted(name for name in self.fields[dag] if name != 'role')
        self.shape(dag, INDEX, names)
        if names != [f'case-{i:03d}' for i in range(1, len(names)+1)] or len(names) > LIMITS['cases']:
            raise ValueError('index ordinal/count profile differs')
        return tree['exercise-run'], {name: self.field(dag, name, 'subdag') for name in names}

    def reached(self, root):
        pending, seen = [('commit', root)], set()
        while pending:
            item = pending.pop()
            if item in seen:
                continue
            if item not in self.objects:
                raise ValueError('dangling typed root/edge')
            if len(seen) >= LIMITS['extract_objects']:
                raise ValueError('typed membership limit exceeded')
            seen.add(item)
            pending.extend((r['dst_kind'], r['dst']) for r in self.children[item])
        return seen

    def case(self, descriptor):
        self.shape(descriptor, DESCRIPTION, {'label','occurrence','target','roots','context','observations'})
        context, observations = [self.field(descriptor, name, 'subdag') for name in ('context','observations')]
        self.shape(context, CONTEXT, {'scenario','parameters','captures','limits','expectations','fixture','sources'})
        self.shape(observations, OBSERVATIONS, {'calls','returns','errors','bad-operation'})
        target, roots = self.identity(descriptor, 'target'), self.ids(descriptor, 'roots')
        parameters = exact(parse(self.field(context, 'parameters', 'bytes')), {'value'})
        if type(parameters['value']) is not int or not -(2**63) <= parameters['value'] < 2**63:
            raise ValueError('context parameter requires I64')
        limits = parse(self.field(context, 'limits', 'bytes'))
        expectations = exact(parse(self.field(context, 'expectations', 'bytes')), {'positions','outcome','invariant'})
        if (limits != LIMITS or expectations['positions'] != [None,3,3]
                or self.field(context, 'scenario', 'string') != 'builtin-map-get'
                or expectations['outcome'] not in ('accept','reject')
                or expectations['invariant'] != (None if expectations['outcome']=='accept' else 'map_get_value')):
            raise ValueError('unsupported context/expectations/limits')
        if len(roots) != 3 or len(set(roots)) != 3 or roots[0] != self.identity(context,'fixture'):
            raise ValueError('exercise roots/fixture differ')
        if self.parents(target) != roots[1:]:
            raise ValueError('CN must retain BOTH indexed checkpoint tips')
        if any(self.parents(root) != [roots[0]] for root in roots[1:]):
            raise ValueError('checkpoint must branch from declared fixture only')
        membership = self.reached(target)
        if any(('commit', root) not in membership for root in roots):
            raise ValueError('indexed root outside exercise target closure')
        occurrence = self.field(descriptor,'occurrence','string')
        for commit in [target, *roots[1:]]:
            tree = self.tree(commit)
            if tree.get('exercise-context') != context:
                raise ValueError('indexed context not THIS exercise context')
            marker = tree.get('exercise-occurrence')
            self.shape(marker, OCCURRENCE, {'occurrence'})
            if self.field(marker,'occurrence','string') != occurrence:
                raise ValueError('target occurrence is not THIS indexed exercise')
        sources = self.ids(context,'sources')
        fixture_entries = self.tree(roots[0])
        if len(sources) != 2 or len(set(sources)) != 2 or any(source not in fixture_entries.values() for source in sources):
            raise ValueError('source scope outside declared fixture')
        for source in sources:
            sample = self.nodes[self.fields[source]['sample']]
            if sample['kind'] != 'literal' or self.datums[sample['target']]['kind'] != 'map':
                raise ValueError('fixture sample requires MAP datum')
            pairs = [r for r in self.rows['map_entries'] if r['oid'] == sample['target']]
            if len(pairs) != 1:
                raise ValueError('fixture MAP entry contract differs')
            key, value = [self.datums[pairs[0][name]] for name in ('key_id','value_id')]
            if key['kind'] != 'string' or key['scalar'] != 'x' or value['kind'] != 'i64' or int(value['scalar']) != parameters['value']:
                raise ValueError('context value differs from fixture MAP input')
        bad_node = self.nodes[self.fields[observations]['bad-operation']]
        bad_kind = self.datums[bad_node['target']]['kind'] if bad_node['kind']=='literal' else None
        if bad_kind not in ('null','bytes'):
            raise ValueError('bad operation requires NULL or ID BYTES')
        bad = None if bad_kind=='null' else self.identity(observations,'bad-operation')
        if bad is not None and ('dag',bad) not in membership:
            raise ValueError('mutation subject outside case closure')
        if (bad is not None) != (expectations['outcome']=='reject'):
            raise ValueError('fault observation disagrees with scenario expectation')
        calls = self.field(observations,'calls','i64')
        returns = parse(self.field(observations,'returns','bytes'))
        if calls != 6 or returns != [parameters['value']]*6 or parse(self.field(observations,'errors','bytes')) != []:
            raise ValueError('unsupported incomplete observation profile')
        return {'description':descriptor,'label':self.field(descriptor,'label','string'),
                'occurrence':self.field(descriptor,'occurrence','string'),'target':target,'roots':roots,
                'context':context,'sources':sources,'parameters':parameters,
                'captures':parse(self.field(context,'captures','bytes')),'expectations':expectations,
                'calls':calls,'bad_operation':bad,'membership':sorted([list(item) for item in membership])}


def catalog(rows, publication):
    facts = Facts(rows)
    run, latest = facts.index(publication)
    facts.shape(run, RUN, {'namespace','scenarios','captures','limits'})
    namespace = facts.field(run,'namespace','string')
    specs = parse(facts.field(run,'scenarios','bytes'))
    validate_cases(specs)
    captures = parse(facts.field(run,'captures','bytes'))
    if facts.field(run,'limits','bytes') != canonical(LIMITS) or not namespace or len(latest) > len(specs):
        raise ValueError('run bounds/namespace differ')
    chain, seen, current = [], set(), publication
    while True:
        if current in seen:
            raise ValueError('publication ancestry cycle')
        seen.add(current)
        this_run, entries = facts.index(current)
        if this_run != run:
            raise ValueError('publication run identity changed')
        chain.append(current)
        parents = facts.parents(current)
        if not entries:
            if parents:
                raise ValueError('P0 empty index must be parentless')
            break
        if len(parents) != 2:
            raise ValueError('PN must have previous-publication first and CN second')
        prior_run, prior = facts.index(parents[0])
        if prior_run != run or len(entries) != len(prior)+1 or any(entries.get(k)!=v for k,v in prior.items()):
            raise ValueError('publication lost/replaced prior description')
        new_case = facts.case(entries[f'case-{len(entries):03d}'])
        if parents[1] != new_case['target']:
            raise ValueError('second parent not indexed CN')
        current = parents[0]
    cases = [facts.case(descriptor) for descriptor in latest.values()]
    for number, case in enumerate(cases):
        expected = specs[number]
        if (case['label'] != expected['label'] or case['occurrence'] != f'{namespace}/exercise-{number+1}'
                or case['parameters']['value'] != expected['value'] or case['captures'] != captures
                or (case['expectations']['outcome']=='reject') != expected['fault']):
            raise ValueError('case context/occurrence differs from run declaration')
    if len({c['occurrence'] for c in cases}) != len(cases):
        raise ValueError('actual exercise occurrence collision')
    return {'publication':publication,'first_parent_chain':list(reversed(chain)), 'namespace':namespace,
            'declared_cases':len(specs),'completed_cases':len(cases),'cases':cases}


def scoped_rows(rows, case):
    available = {tuple(item) for item in case['membership']}
    owners = {'objects':None,'edges':None,'datums':'datum','map_entries':'datum','nodes':'node',
              'dags':'dag','fields':'dag','tree_entries':'tree','commits':'commit'}
    result = {}
    for table, kind in owners.items():
        if table == 'objects':
            result[table] = [r for r in rows[table] if (r['kind'],r['oid']) in available]
        elif table == 'edges':
            result[table] = [r for r in rows[table] if (r['src_kind'],r['src']) in available]
        else:
            key = 'dag' if table=='fields' else 'oid'
            result[table] = [r for r in rows[table] if (kind,r[key]) in available]
    result['roots'] = [{'checkpoint':i,'commit_id':root,'expected_positions':case['expectations']['positions'][i]}
                       for i,root in enumerate(case['roots'])]
    return result


def normalize(repository, publication, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        rows, stats = extract({'repository':str(repository),'roots':[publication]})
        projected = catalog(rows, publication)
    except Exception as error:
        (directory/'projection-error.json').write_bytes(canonical({'stage':'extract/catalog','error':repr(error)}))
        raise
    for table in SCHEMA:
        (directory/(table+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows[table]))
    (directory/'catalog.json').write_bytes(canonical(projected))
    (directory/'stats.json').write_text(json.dumps(stats,sort_keys=True,indent=2)+'\n')
    return rows, projected, stats
