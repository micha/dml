"""Private process fixture: barriers only here, never in the installed runner."""
import json
from pathlib import Path
import sys

from daggerml import ObjectId
from daggerml import local

path, binding, inputs, phase, barrier = sys.argv[1:]
original = local._execute if phase == "prepared" else local._finalize


def paused(context, *args, **kwargs):
    staging = Path(barrier + ".tmp")
    staging.write_text(json.dumps({name: str(value) if isinstance(value, ObjectId) else value
                                  for name, value in context.__dict__.items()}), encoding="utf-8")
    staging.replace(barrier)
    # The harness terminates this direct parent after observing the durable barrier.
    # Closing stdin would release it, so a failed harness cannot leave an indefinite fixture.
    sys.stdin.readline()
    return original(context, *args, **kwargs)


if phase == "prepared":
    local._execute = paused
else:
    local._finalize = paused
local.run_step(path, head_ref="main", intent_uri="urn:example:add-i64", binding=ObjectId.from_hex(binding),
               inputs=ObjectId.from_hex(inputs), scratch_dir=Path(barrier).parent)
