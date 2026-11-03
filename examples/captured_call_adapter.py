"""ONE fixed in-process adapter, deliberately distinct from the LOCAL leaf adapter."""

from pathlib import Path
import types

import captured_calls as p
from captured_call_session import LeafFailure, Session, SessionError


def execute(path, request, *, workspace, receipt=None):
    """No outer subprocess, arbitrary URI dispatch, timeout or cleanup fiction.

    Captured byte identity is checked through native C/B/E before compiling ONLY
    the supported fixed logical source. Persistence/validation/custody uncertainty
    leaves initial T/partial phases; deterministic logical errors can record failure.
    """
    if request.action != "execute-fresh" or request.reused is not None:
        raise ValueError("outer hit cannot enter adapter or create an attempt")
    session = Session(path, request, workspace, receipt)
    source = p.outer_sources()[0]
    logical = types.ModuleType("captured_double_sum")
    try:
        exec(compile(source, str(Path(__file__).with_name("captured_call_funcs.py")), "exec"), logical.__dict__)
        func = logical.double_sum(*session.tokens, session.nodes, session.invoker)
        result = func(session.input)
        return session.finish(result)
    except (SessionError, ValueError, OverflowError) as error:
        # Session methods mark native/public-validation exceptions UNKNOWN first.
        # A caught interface error cannot subsequently finish successfully.
        return session.fail(error)
    finally:
        session.ended = True
