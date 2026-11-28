"""Typed operands and observations for direct calls to example workflows."""

import re


def evidence_text(text):
    # The Quint evidence writer cannot represent quotes, backslashes or non-ASCII text.
    return text if re.fullmatch(r"[\x20-\x21\x23-\x5b\x5d-\x7e]*", text) else "hex:" + text.encode("utf-8").hex()


class BytesSubclass(bytes):
    pass


class IntSubclass(int):
    pass


class PathProbe:
    def __init__(self, path):
        self.path = path
        self.uses = 0

    def __fspath__(self):
        self.uses += 1
        return str(self.path)


def operand_value(tag, value, resolve_id):
    if tag == "id":
        return bytes.fromhex(resolve_id(value))
    if tag == "none" and not value:
        return None
    if tag == "bool":
        return {"true": True, "false": False}[value]
    return {
        "text": str, "bytes": str.encode, "hex": bytes.fromhex,
        "bytearray": bytearray.fromhex, "bytes-subclass": lambda raw: BytesSubclass(bytes.fromhex(raw)),
        "int": int, "int-subclass": IntSubclass, "float": float,
    }[tag](value)


def tagged(operand):
    tag, separator, value = operand.partition(":")
    if not separator:
        raise ValueError(f"missing type tag in Python operand {operand!r}")
    return tag, value


def observe_call(function, path, operands, resolve_id):
    args, kwargs = [], {}
    tokens = iter(operands)
    for operand in tokens:
        tag, value = tagged(operand)
        if tag == "keyword":
            if value in kwargs or (raw := next(tokens, None)) is None:
                raise ValueError(f"duplicate or missing operand for Python keyword {value!r}")
            kind, payload = tagged(raw)
            kwargs[value] = operand_value(kind, payload, resolve_id)
        else:
            args.append(operand_value(tag, value, resolve_id))
    probe = PathProbe(path)
    try:
        result = function(probe, *args, **kwargs)
    except Exception as failure:
        return None, type(failure).__name__, str(failure), probe.uses
    return result, "", "", probe.uses
