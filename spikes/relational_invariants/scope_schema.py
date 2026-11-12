"""Case-scoped oracle inputs; no DML imports or validation decisions."""

SCOPE_SCHEMA = {
    'composition_scopes': {'scope_id': 'INTEGER', 'commit_id': 'VARCHAR', 'inputs_name': 'VARCHAR',
                           'composition_name': 'VARCHAR', 'depth': 'INTEGER'},
    'candidate_scopes': {'scope_id': 'INTEGER', 'commit_id': 'VARCHAR', 'attempt_id': 'VARCHAR',
                         'phase': 'VARCHAR', 'request': 'VARCHAR', 'binding': 'VARCHAR',
                         'inputs': 'VARCHAR', 'intent': 'VARCHAR', 'job_document': 'JSON',
                         'expected_document': 'JSON', 'receipt_document': 'JSON',
                         'bundle_root': 'VARCHAR', 'bundle_sha256': 'VARCHAR'},
    'selection_scopes': {'scope_id': 'INTEGER', 'commit_id': 'VARCHAR', 'slot': 'VARCHAR',
                         'binding_name': 'VARCHAR', 'inputs_name': 'VARCHAR', 'intent': 'VARCHAR'},
    'resolution_scopes': {'scope_id': 'INTEGER', 'commit_id': 'VARCHAR', 'inputs_name': 'VARCHAR',
                          'composition_name': 'VARCHAR', 'control': 'VARCHAR', 'depth': 'INTEGER',
                          'intent': 'VARCHAR', 'binding_name': 'VARCHAR'},
    'transition_scopes': {'transition_id': 'INTEGER', 'kind': 'VARCHAR', 'before_commit': 'VARCHAR',
                          'after_commit': 'VARCHAR', 'slot': 'VARCHAR', 'inputs': 'VARCHAR'},
    'reuse_scopes': {'reuse_id': 'INTEGER', 'submission': 'VARCHAR', 'request': 'VARCHAR',
                     'satisfaction': 'VARCHAR', 'selection': 'VARCHAR', 'basis': 'VARCHAR', 'slot': 'VARCHAR'},
}
