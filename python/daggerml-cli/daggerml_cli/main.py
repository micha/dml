"""Entry point for the ``dml`` command."""

from __future__ import annotations

import argparse
import importlib


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(prog="dml", description="DaggerML CLI")
  parser.add_argument(
    "--version",
    action="store_true",
    help="Show the installed DaggerML core version.",
  )
  return parser


def main() -> int:
  args = build_parser().parse_args()
  if args.version:
    daggerml = importlib.import_module("daggerml")
    print(daggerml.version())
    return 0

  print("dml CLI scaffold is installed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
