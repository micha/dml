"""New indexed profile; generic extractor and shared publication convention unchanged."""

import json
from pathlib import Path

from incremental.identity import canonical,parse,exact
from normalizer import extract
from schema import SCHEMA
from shared_index.project import Facts
from .exercise import INDEX,RUN,DESC,CTX,OBS,LIMITS,SPECS


def index(facts,commit):
    tree=facts.tree(commit)
    exact(dict(tree),{'exercise-index','exercise-run'})
    dag=tree['exercise-index']
    names=sorted(name for name in facts.fields[dag] if name!='role')
    facts.shape(dag,INDEX,names)
    if names!=[f'case-{n:03d}' for n in range(1,len(names)+1)] or len(names)>16:
        raise ValueError('existing-case index ordinal/count differs')
    return tree['exercise-run'],{name:facts.field(dag,name,'subdag') for name in names}


def case(facts,descriptor):
    facts.shape(descriptor,DESC,{'label','occurrence','target','roots','context','observations'})
    context=facts.field(descriptor,'context','subdag');observations=facts.field(descriptor,'observations','subdag')
    facts.shape(context,CTX,{'spec','function','captures','limits','method','subject','expectations'})
    facts.shape(observations,OBS,{'assertion-completed','validator-observations','calls'})
    target=facts.identity(descriptor,'target');roots=facts.ids(descriptor,'roots')
    membership=facts.reached(target)
    if not 2<=len(roots)<=4 or len(set(roots))!=len(roots) or facts.parents(target)!=[roots[-1]]:
        raise ValueError('existing case roots/anchor differ')
    if any(('commit',root) not in membership for root in roots):raise ValueError('case root not retained')
    for i in range(1,len(roots)):
        if facts.parents(roots[i])!=[roots[i-1]]:raise ValueError('original case commits not sequential from fixture')
    if facts.tree(target).get('exercise-context')!=context:raise ValueError('THIS context not linked by target')
    marker=facts.tree(target).get('exercise-occurrence')
    facts.shape(marker,'existing-exercise-occurrence-v1',{'occurrence'})
    occurrence=facts.field(descriptor,'occurrence','string')
    if facts.field(marker,'occurrence','string')!=occurrence:raise ValueError('actual case occurrence differs')
    subject=facts.identity(context,'subject');method=facts.field(context,'method','string')
    if ('dag',subject) not in membership or method not in ('node','trace','arguments'):
        raise ValueError('semantic subject/method unavailable')
    if parse(facts.field(context,'limits','bytes'))!=LIMITS:raise ValueError('case limits differ')
    spec=exact(parse(facts.field(context,'spec','bytes')),{'label','function','fault'})
    expected=exact(parse(facts.field(context,'expectations','bytes')),{'accepted'})
    if type(expected['accepted']) is not bool:raise ValueError('expectation requires bool')
    observed=parse(facts.field(observations,'validator-observations','bytes'))
    calls=parse(facts.field(observations,'calls','bytes'))
    if facts.field(observations,'assertion-completed','bool')!='True':raise ValueError('original body incomplete')
    primary=[o for o in observed if o['subject']==subject and o['method']==method and o['commit']==roots[-1]]
    if not primary:raise ValueError('primary observation missing')
    return {'label':facts.field(descriptor,'label','string'),'occurrence':occurrence,'target':target,'roots':roots,
            'context':context,'subject':subject,'method':method,'spec':spec,'expected':expected['accepted'],
            'observed':primary[-1]['accepted'],'calls':calls,'function':facts.field(context,'function','string'),
            'captures':parse(facts.field(context,'captures','bytes')),
            'membership':sorted([list(item) for item in membership])}


def catalog(rows,publication):
    facts=Facts(rows);run,latest=index(facts,publication)
    facts.shape(run,RUN,{'namespace','specs','captures','limits'})
    namespace=facts.field(run,'namespace','string')
    captures=parse(facts.field(run,'captures','bytes'))
    if parse(facts.field(run,'specs','bytes'))!=SPECS or parse(facts.field(run,'limits','bytes'))!=LIMITS:
        raise ValueError('unsupported original test profile')
    current=publication;seen=set();chain=[]
    while True:
        if current in seen:raise ValueError('publication cycle')
        seen.add(current);chain.append(current)
        same,entries=index(facts,current)
        if same!=run:raise ValueError('run changed')
        parents=facts.parents(current)
        if not entries:
            if parents:raise ValueError('P0 not parentless')
            break
        if len(parents)!=2:raise ValueError('publication requires previous-first/CN-second')
        prior_run,prior=index(facts,parents[0])
        if prior_run!=run or len(prior)+1!=len(entries) or any(entries.get(k)!=v for k,v in prior.items()):
            raise ValueError('index prefix changed')
        if facts.identity(entries[f'case-{len(entries):03d}'],'target')!=parents[1]:raise ValueError('CN parent differs')
        current=parents[0]
    cases=[case(facts,description) for description in latest.values()]
    for number,item in enumerate(cases):
        if (item['spec']!=SPECS[number] or item['label']!=SPECS[number]['label'] or item['captures']!=captures
                or item['occurrence']!=f'{namespace}/exercise-{number+1}'
                or item['expected']!=(SPECS[number]['function']=='equal-sources')):
            raise ValueError('case declaration differs')
    return {'publication':publication,'first_parent_chain':list(reversed(chain)),'cases':cases,'namespace':namespace}


def normalize(repository,publication,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    try:
        rows,stats=extract({'repository':str(repository),'roots':[publication]})
        projected=catalog(rows,publication)
    except Exception as error:
        (directory/'projection-error.json').write_bytes(canonical({'error':repr(error)}))
        raise
    for table in SCHEMA:
        (directory/(table+'.jsonl')).write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in rows[table]))
    (directory/'catalog.json').write_bytes(canonical(projected))
    (directory/'stats.json').write_text(json.dumps(stats,sort_keys=True)+'\n')
    return rows,projected,stats
