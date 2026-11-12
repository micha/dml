import ast
from pathlib import Path

import pytest

from incremental.identity import canonical, digest, parse
from incremental.stages import load_transfer


def test_one_real_portable_seed_import_root_rejection_and_storage_abort(control, tmp_path):
    dml = control.dml
    with dml.Repository(control.path) as repo, repo.write() as tx:
        literal = tx.put_literal(tx.put_datum(42))
        dag = tx.put_dag(root=literal, bindings={'sample': literal})
        seed = tx.put_commit(tx.put_tree({'seed': dag}))
        tx.create_ref('CONTROL-seed', seed)
    transfer = load_transfer(dml)
    raw = transfer.export_commit(control.path, commit=seed)  # ALL owners closed first.
    document = parse(raw)
    assert document['root'] == str(seed)
    destination = tmp_path / 'imported.dml'
    with dml.Repository(destination, create=True):
        pass
    result = transfer.import_commit(destination, raw, ref='seed')
    assert result.commit == seed
    assert transfer.export_commit(destination, commit=seed) == raw
    with dml.Repository(destination) as repo, repo.read() as tx:
        assert tx.get_ref('seed') == seed
        assert tx.get_datum(tx.get_node(tx.get_dag(dict(tx.get_tree(tx.get_commit(seed).tree))['seed']).root).datum).value == 42
    bad = {**document, 'root': 'f' * 32}
    with pytest.raises(transfer.TransferError):
        transfer.import_commit(destination, canonical(bad), ref='bad-root')
    with dml.Repository(destination) as repo, repo.read() as tx:
        with pytest.raises(dml.NotFoundError):
            tx.get_ref('bad-root')
        with pytest.raises(dml.NotFoundError):
            tx.get_commit(dml.ObjectId.from_hex('f' * 32))
    with pytest.raises(ValueError):
        with dml.Repository(destination) as repo, repo.write() as tx:
            tx.create_ref('aborted', seed)
            raise ValueError('deliberate before-commit bootstrap failure')
    with dml.Repository(destination) as repo, repo.read() as tx:
        with pytest.raises(dml.NotFoundError):
            tx.get_ref('aborted')
        assert tx.get_ref('seed') == seed
    assert digest(transfer.export_commit(destination, commit=seed)) == digest(raw)


def test_actual_owned_byte_variants_not_fake_revision_labels(pins):
    root = Path(pins['root'])
    for left, right, name in [('candidate-A/python/daggerml/daggerml',
                               'candidate-B/python/daggerml/daggerml', 'builtin.py'),
                              ('P1', 'P2', 'normalizer.py'), ('C1', 'C2', 'checker.py')]:
        original, variant = (root / left / name).read_bytes(), (root / right / name).read_bytes()
        assert original != variant
        assert ast.dump(ast.parse(original)) == ast.dump(ast.parse(variant))
    original = (root / 'C1/checks.sql').read_text()
    disabled = (root / 'C-disabled/checks.sql').read_text()
    assert "SELECT 'map_get_value'," in original
    assert "SELECT 'map_get_value'," not in disabled
    assert "SELECT 'missing_object'" in disabled
    assert "SELECT 'empty_dataset'" in disabled
    # This is STATIC sensitivity preparation, not a SQL invocation/verdict proof.
