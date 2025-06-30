"""Command line interface for usage-report."""
from __future__ import annotations

import argparse
import sys
from pprint import pprint

from .api import SimAPI, SimAPIError
from .slurm import fetch_usage
from .report import create_report, write_report_csv


def _add_api_parser(sub: argparse._SubParsersAction) -> None:
    api_parser = sub.add_parser("api", help="Fetch LRZ SIM API user info")
    api_parser.add_argument("user_id", help="LRZ user identifier")
    api_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )


def _add_slurm_parser(sub: argparse._SubParsersAction) -> None:
    slurm_parser = sub.add_parser("slurm", help="Calculate Slurm usage")
    slurm_parser.add_argument("user_id", help="LRZ user identifier")
    slurm_parser.add_argument("-S", "--start", required=True, help="Start date YYYY-MM-DD")
    slurm_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")


def _add_report_parser(sub: argparse._SubParsersAction) -> None:
    report_parser = sub.add_parser("report", help="Generate combined report")
    report_parser.add_argument("user_id", help="LRZ user identifier")
    report_parser.add_argument("-S", "--start", required=True, help="Start date YYYY-MM-DD")
    report_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    report_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Usage reporting utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_api_parser(sub)
    _add_slurm_parser(sub)
    _add_report_parser(sub)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "api":
        api = SimAPI(netrc_file=args.netrc_file)
        try:
            data = api.fetch_user(args.user_id)
        except SimAPIError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        pprint(data)
    elif args.command == "slurm":
        usage = fetch_usage(args.user_id, args.start, args.end)
        pprint(usage)
    elif args.command == "report":
        try:
            report = create_report(
                args.user_id,
                args.start,
                args.end,
                netrc_file=args.netrc_file,
            )
        except SimAPIError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        output_path = write_report_csv(
            report,
            "output",
            f"{args.user_id}.csv",
            start=args.start,
            end=args.end,
        )

        report_with_period = report.copy()
        report_with_period["period_start"] = args.start
        report_with_period["period_end"] = args.end

        pprint(report_with_period)
        print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI execution
    raise SystemExit(main())
