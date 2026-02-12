"""Entry points for the example DaggerML adapter."""

from __future__ import annotations


def adapter_entrypoint() -> str:
  return "example"


def main() -> int:
  print("daggerml adapter scaffold: example")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
