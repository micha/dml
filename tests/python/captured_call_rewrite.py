"""TEST-PRIVATE coherent native history rewriting through typed PUBLIC APIs.

No packed codec/hash or execution. Parent-first copy permits actual commit metadata
and existing public JSON framing to follow rewritten IDs; historical paths stay inert.
"""

import json

import daggerml as d


def rewrite(source, destination, root, corrupt):
    mapped = {}
    def bytes_value(raw):
        if len(raw) == 16:
            for (kind, old), new in mapped.items():
                if old.bytes == raw:
                    return new.bytes
        if raw.startswith(b"{"):
            try:
                got = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                return raw
            def walk(value):
                if type(value) is str:
                    for (kind, old), new in mapped.items():
                        if value == str(old):
                            return str(new)
                if type(value) is list:
                    return [walk(v) for v in value]
                if type(value) is dict:
                    return {n: walk(v) for n, v in value.items()}
                return value
            return json.dumps(walk(got), separators=(",", ":")).encode()
        return raw
    with d.Repository(source) as src, src.read() as read, d.Repository(destination, create=True) as dst, dst.write() as write:
        def copy(kind, old):
            key = (kind, old)
            if key in mapped:
                return mapped[key]
            if kind == "commit":
                got = read.get_commit(old)
                parents = tuple(copy("commit", p) for p in got.parents)
                new = write.put_commit(copy("tree", got.tree), parents=parents)
            elif kind == "tree":
                new = write.put_tree({n: copy("dag", v) for n, v in read.get_tree(old).items()})
            elif kind == "dag":
                got = read.get_dag(old)
                fields = {n: copy("node", v) for n, v in got.bindings.items()}
                root_node = copy("node", got.root)
                fields, root_node = corrupt(read, write, old, fields, root_node)
                new = write.put_dag(root=root_node, bindings=fields)
            elif kind == "node":
                got = read.get_node(old)
                new = write.put_literal(copy("datum", got.datum)) if isinstance(got, d.LiteralNode) else write.put_subdag(copy("dag", got.dag))
            else:
                got = read.get_datum(old)
                if got.kind == "bytes":
                    got = d.Datum.bytes(bytes_value(got.value))
                elif got.kind in ("list", "set"):
                    got = d.Datum(got.kind, tuple(copy("datum", v) for v in got.value))
                elif got.kind == "map":
                    got = d.Datum.map((copy("datum", k), copy("datum", v)) for k, v in got.value)
                new = write.put_datum(got)
            mapped[key] = new
            return new
        result = copy("commit", root)
        write.create_ref("rewritten", result)
    return result, mapped
