"""Trusted cooperative child: add two pinned I64 arguments and publish a DAG."""
import daggerml as dml
from daggerml.local import child_context, publish_result

context = child_context()
with dml.Repository(context.repository_path) as repo, repo.write() as tx:
    values = []
    for name in ("left", "right"):
        node = tx.get_node(tx.lookup_node(context.inputs, name))
        if not isinstance(node, dml.LiteralNode):
            raise ValueError("addition requires literal arguments")
        datum = tx.get_datum(node.datum)
        if datum.kind != "i64":
            raise ValueError("addition requires I64 arguments")
        values.append(datum.value)
    node = tx.put_literal(tx.put_datum(sum(values)))
    result = tx.put_dag(root=node, bindings={"result": node})
    publish_result(tx, context, result)
