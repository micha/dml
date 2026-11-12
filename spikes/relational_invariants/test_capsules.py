"""Pure projection guards; malformed header evidence must remain explicit."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capsules import project


def facts(raw, *, kind='bytes', node_kind='literal'):
    return {'fields': [{'dag':'S','name':'validation','node':'v'}, {'dag':'V','name':'expected','node':'h'}],
            'nodes': [{'oid':'v','kind':'subdag','target':'V'}, {'oid':'h','kind':node_kind,'target':'data'}],
            'datums': [{'oid':'data','kind':kind,'scalar':raw.hex()}]}


@pytest.mark.parametrize('raw,message', [
    (b'\xff','codec'), (b'{','Expecting'), (b'{"x":1,"x":2}','duplicate'),
    (b'{"x":NaN}','nonfinite'), (b'[]','JSON object'), (b'x'*8193,'exceeds8192'),
])
def test_bad_headers_produce_explicit_error_rows(raw, message):
    rows = project(facts(raw))
    expected = next(row for row in rows if row['field']=='expected')
    assert message in expected['parse_error']
    assert expected['document'] is None
    assert len(rows)==3  # Missing job/observation also retained as error rows.


def test_exact_8192_header_boundary_remains_allowed():
    expected = next(row for row in project(facts(b'{}'+b' '*8190)) if row['field']=='expected')
    assert expected['parse_error'] is None and expected['byte_count']==8192
    assert expected['document']=='{}'


@pytest.mark.parametrize('kind,node_kind', [('string','literal'), ('bytes','subdag')])
def test_wrong_native_field_kinds_are_not_silently_dropped(kind, node_kind):
    expected = next(row for row in project(facts(b'{}', kind=kind,node_kind=node_kind)) if row['field']=='expected')
    assert expected['parse_error']=='header is not a BYTES literal'
