"""Command-line interface for portfolio risk analytics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .analytics import analyze_portfolio


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate transparent portfolio return and risk metrics.")
    parser.add_argument("input", type=Path, help="JSON input containing weights and aligned price histories")
    parser.add_argument("-o", "--output", type=Path, help="write result JSON to this path (default: stdout)")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = analyze_portfolio(data)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
