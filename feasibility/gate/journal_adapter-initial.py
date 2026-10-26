"""Attempted public journal adapter (v1/v2 shape). Not end-to-end integrated.
The adapter refuses invented mappings and treats ack failure as durable intent.
Callers supply a real Journal instance whose sandbox they are authorized to own.
"""
from pathlib import Path
from gate import Rejected, digest, need, observe

class JournalAdapter:
    def __init__(self, journal):
        self.journal = journal
    def validate_bindings(self, ticket, bindings):
        # UUID->file relabeling is NOT physical identity equivalence.
        need(set(bindings) == set(ticket['victims'].values()), 'incomplete physical identity mapping')
        for manager_id, journal_id in bindings.items():
            row = self.journal.resource(journal_id)
            need(row['physical'] == manager_id, 'unsupported physical identity bridge')
    def reserve(self, ticket, bindings):
        self.validate_bindings(ticket, bindings)
        need(self.journal.snapshot()['revision'] == ticket['root_revision'], 'stale journal snapshot')
        return self.journal.reserve(list(bindings.values()), ticket['root_revision'],
                                    plan_digest=ticket['plan_digest'])
    def apply(self, gate, ticket, reservation, plan, bindings):
        self.validate_bindings(ticket, bindings)
        gate.check(ticket, plan)
        authoritative = self.journal.verify(reservation)
        need(authoritative['plan_digest'] == digest(Path(plan).read_bytes()), 'journal plan mismatch')
        need(authoritative['victims'] == sorted(bindings.values()), 'journal victim mismatch')
        self.journal.begin_effect(reservation)
        # Global durable fence survives this nontransactional subprocess boundary.
        gate.check(ticket, plan)
        from gate import cli
        cli(gate.root, 'apply', '-input=false', '-no-color', str(plan))
        result = observe(gate.root)
        # journal-v1 ack observes its own file paths, not these terraform_data IDs.
        # It cannot truthfully acknowledge the manager effect without a backend seam.
        self.journal.ack(reservation)
        return result

def probe(base, manager_root, manager_ticket):
    import importlib.util
    source = Path(__file__).resolve().parent.parent/'journal/journal.py'
    spec = importlib.util.spec_from_file_location('candidate_journal', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sandbox = base/'real-journal-sandbox'
    sandbox.mkdir()
    journal = module.Journal(base/'real-journal.db',sandbox,
                             runtime_root=Path(__file__).resolve().parent/'runtime')
    results = {'contract':module.CONTRACT_VERSION,
               'journal_source_digest':digest(source.read_bytes()),
               'adapter_status':'identity/backend integration blocked'}
    def rejected(fn, reason):
        try:
            fn()
        except (module.Rejected, Rejected) as e:
            need(reason in str(e), 'unexpected rejection: '+str(e))
            return str(e)
        raise AssertionError('expected rejection: '+reason)
    try:
        ident = journal.create_file('synthetic-file',b'gate adapter synthetic bytes')
        journal.adopted(ident)
        journal.member('real-member')
        journal.commit('real-member','commit-one',operational=[ident])
        journal.head('real-member','main',None,'commit-one')
        snap=journal.snapshot()
        need(ident in snap['roots']['retained'], 'root extraction')
        results['actual_full_history_retention']=rejected(
            lambda:journal.reserve([ident],snap['revision'],manager_ticket['plan_digest']), 'full-history retained')
        journal.member('new-member')
        results['actual_stale_membership']=rejected(
            lambda:journal.reserve([ident],snap['revision'],manager_ticket['plan_digest']), 'stale revision')
        journal.excise(ident)
        snap=journal.snapshot()
        adapter_ticket=dict(manager_ticket,root_revision=snap['revision'])
        bindings={next(iter(manager_ticket['victims'].values())):ident}
        adapter=JournalAdapter(journal)
        results['physical_bridge_rejection']=rejected(
            lambda:adapter.reserve(adapter_ticket,bindings), 'unsupported physical identity bridge')
        # Deliberately attempt a mismatched external effect, independently of the
        # correctly rejecting adapter, to falsify "apply success means ack".
        reservation=journal.reserve([ident],snap['revision'],manager_ticket['plan_digest'])
        journal.verify(reservation)
        journal.begin_effect(reservation)
        results['actual_durable_publication_fence']=rejected(
            lambda:journal.member('late-member'), 'global destruction fence active')
        from gate import cli
        cli(manager_root,'apply','-input=false','-no-color',str(manager_root/'cleanup.tfplan'))
        need(observe(manager_root)['manifest']=={}, 'actual manager cleanup')
        results['mismatched_effect_ack_rejection']=rejected(
            lambda:journal.ack(reservation), 'absence not observed')
        results['durable_status_after_mismatch']=journal.verify(reservation)['status']
        # The real file journal's own supported cleanup completes truthfully.
        journal.effect(reservation)
        results['file_backend_recovery']=journal.ack(reservation)['status']
        results['limitations']='No managed terraform_data registration or equivalent file backend mapping; generic gate rejects rather than inventing one.'
        return results
    finally:
        journal.close()
