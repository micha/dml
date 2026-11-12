"""Replaceable fixed checker payload; exactly owning negative violation, no native IO."""
from pathlib import Path

from incremental.identity import canonical
from per_exercise.capsules import read


def assert_agreement(case, verdict):
    violations = verdict['violations']
    if case['expectations']['outcome'] == 'accept':
        if not verdict['accepted'] or violations:
            raise AssertionError('positive case unexpectedly rejected')
    else:
        if (verdict['accepted'] or not violations or
                any(row['invariant'] != 'map_get_value' or row['subject'] != case['bad_operation']
                    for row in violations)):
            raise AssertionError('negative case missing exact sole owning counterexample')
    return True


def check(upstream, database, directory, spec):
    from shared_index.check import check_case
    capsule = read(Path(upstream) / 'capsule.json')
    case = capsule['case']
    if (case['label'] != spec['label'] or case['parameters'] != {'value': spec['value']}
            or (case['expectations']['outcome'] == 'reject') != spec['fault']):
        raise ValueError('checker case input differs')
    verdict = check_case(database, capsule['rows'], case, output_directory=Path(directory) / 'check')
    try:
        agreement = assert_agreement(case, verdict)
    except AssertionError:
        agreement = False
    result = {'verdict': verdict, 'agreement': agreement, 'spec': spec,
              'producer_occurrence': case['occurrence']}
    (Path(directory) / 'verdict.json').write_bytes(canonical(result))
    return agreement
