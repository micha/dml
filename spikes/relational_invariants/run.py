"""Run isolated spike components against this worktree's native build."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def bootstrap():
    package = ROOT / "python/daggerml/daggerml"
    if "daggerml" in sys.modules:
        if Path(sys.modules["daggerml"].__file__).resolve() != package / "__init__.py":
            raise RuntimeError("spike requires this worktree's DML package")
        return
    build = ROOT / "build/spike-native"
    spec = importlib.util.spec_from_file_location("daggerml", package / "__init__.py",
                                                submodule_search_locations=[str(package), str(build)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["daggerml"] = module
    spec.loader.exec_module(module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=("exercise", "normalize", "check", "all"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--checkpoints", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    # Checker can run without importing DML or opening any repository.
    from checker import check
    if args.component == "check":
        result = check(args.path)
    else:
        bootstrap()
        from exerciser import exercise
        from normalizer import normalize
        if args.component == "exercise":
            result = exercise(args.path, args.checkpoints)
        elif args.component == "normalize":
            if args.output is None:
                parser.error("normalize requires --output DIRECTORY")
            database, stats = normalize(args.path, args.output)
            result = {"database": str(database), "normalizer": stats}
        else:
            exercise(args.path, args.checkpoints)
            database, stats = normalize(args.path / "manifest.json", args.path / "normalized")
            result = {"normalizer": stats, "checker": check(database)}
    print(json.dumps(result, indent=2))
    if args.component in ("all", "check"):
        verdict = result["checker"] if args.component == "all" else result
        return bool(verdict["violations"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
