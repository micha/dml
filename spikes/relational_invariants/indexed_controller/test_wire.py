"""Pure admission/key controls, no stage/native/SQL activation."""
import copy
import os
from pathlib import Path

import pytest

from incremental.identity import key,digest
from indexed_controller.driver import envelope,Controller
from indexed_controller.pins import verify


@pytest.fixture(scope='module')
def pins():return verify(Path(os.environ['INDEXED_CONTROLLER_PINS']))


def upstream(stage='E'):
    return {'key':digest((stage+'key').encode()),'digest':digest((stage+'artifact').encode()),'roots':['a'*32]}


def test_fixed_indexed_profile_includes_one_publication_boundary(pins):
    e=envelope(pins,'E');p=envelope(pins,'P',variant='P1',upstream=upstream())
    assert e['context']=={'profile':'indexed-original16-v1','cases':16}
    assert p['context']['roots']==['a'*32]
    assert p['dependencies']['upstream_key']==upstream()['key']


def test_candidate_real_bytes_invalidate_exercise(pins):
    assert pins['payloads']['A']!=pins['payloads']['B']
    assert key(envelope(pins,'E',candidate='A'))!=key(envelope(pins,'E',candidate='B'))


def test_projector_real_bytes_invalidate_only_downstream(pins):
    old=key(envelope(pins,'E'))
    assert key(envelope(pins,'P',variant='P1',upstream=upstream()))!=key(envelope(pins,'P',variant='P2',upstream=upstream()))
    altered=copy.deepcopy(pins);altered['payloads']['P1']=digest(b'changed projector')
    assert key(envelope(altered,'E'))==old


def test_checker_real_bytes_do_not_change_upstream_keys(pins):
    olde=key(envelope(pins,'E'));oldp=key(envelope(pins,'P',variant='P1',upstream=upstream()))
    assert key(envelope(pins,'C',variant='C1',upstream=upstream('P')))!=key(envelope(pins,'C',variant='C2',upstream=upstream('P')))
    altered=copy.deepcopy(pins);altered['payloads']['C1']=digest(b'changed checker')
    assert key(envelope(altered,'E'))==olde
    assert key(envelope(altered,'P',variant='P1',upstream=upstream()))==oldp


@pytest.mark.parametrize('stage',['P','C'])
def test_upstream_key_changed_even_with_equal_artifact_invalidate(stage,pins):
    input=upstream();changed={**input,'key':digest(b'changed candidate outputs equal')}
    variant='P1' if stage=='P' else 'C1'
    assert key(envelope(pins,stage,variant=variant,upstream=input))!=key(envelope(pins,stage,variant=variant,upstream=changed))


@pytest.mark.parametrize('candidate',['latest','',None])
def test_unrecognized_candidate_never_falls_back(pins,candidate):
    with pytest.raises(ValueError):envelope(pins,'E',candidate=candidate)


@pytest.mark.parametrize('roots',[[],['a'*32,'b'*32]])
def test_missing_or_multiple_publications_rejected(pins,roots):
    with pytest.raises(ValueError):envelope(pins,'P',variant='P1',upstream={**upstream(),'roots':roots})


def test_error_outcome_result_does_not_require_missing_payload(tmp_path):
    class FakeStore:
        def terminal(self,terminal):
            return {},{'key':digest(b'failed')},{'status':'error'},{'name':'missing','sha256':digest(b'raw')},{'stage':'E'}
    controller=Controller.__new__(Controller);controller.store=FakeStore();controller.directory=tmp_path
    result=controller.result('CONTROLfakeT','CONTROLfakeQ',True)
    assert result['status']=='error' and result['roots']==[]
