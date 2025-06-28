"""Command line interface for usage-report."""
from __future__ import annotations

import argparse
import sys
from pprint import pprint

from .api import SimAPI, SimAPIError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch user information from LRZ SIM API")
    parser.add_argument("user_id", help="LRZ user identifier")
    parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api = SimAPI(netrc_file=args.netrc_file)
    try:
        data = api.fetch_user(args.user_id)
    except SimAPIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    pprint(data)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI execution
    raise SystemExit(main())
