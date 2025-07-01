"""Command line interface for usage-report."""
from __future__ import annotations

import argparse
import sys
from pprint import pprint
from datetime import datetime, timedelta

from .api import SimAPI, SimAPIError
from .slurm import fetch_usage
from .sreport import fetch_active_usage
from .report import create_report, write_report_csv


def expand_month(month: str) -> tuple[str, str]:
    """Return start and end dates for ``month`` (``YYYY-MM``)."""
    dt = datetime.strptime(month, "%Y-%m")
    start = dt.replace(day=1)
    if dt.month == 12:
        next_month = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_month = dt.replace(month=dt.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")


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
    grp = slurm_parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("-S", "--start", dest="start", help="Start date YYYY-MM-DD")
    grp.add_argument("--month", help="Month YYYY-MM")
    slurm_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    slurm_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )


def _add_report_parser(sub: argparse._SubParsersAction) -> None:
    report_parser = sub.add_parser("report", help="Generate combined report")
    report_parser.add_argument("user_id", help="LRZ user identifier")
    grp = report_parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("-S", "--start", dest="start", help="Start date YYYY-MM-DD")
    grp.add_argument("--month", help="Month YYYY-MM")
    report_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    report_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )
    report_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )


def _add_active_parser(sub: argparse._SubParsersAction) -> None:
    active_parser = sub.add_parser(
        "active", help="Calculate usage for active users via sreport"
    )
    grp = active_parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("-S", "--start", dest="start", help="Start date YYYY-MM-DD")
    grp.add_argument("--month", help="Month YYYY-MM")
    active_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    active_parser.add_argument(
        "-u",
        "--user",
        dest="active_users",
        action="append",
        required=True,
        help="Active user identifier (can be used multiple times)",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Usage reporting utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_api_parser(sub)
    _add_slurm_parser(sub)
    _add_report_parser(sub)
    _add_active_parser(sub)
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
        start = args.start
        end = args.end
        if args.month:
            if args.end:
                print("--end cannot be used with --month", file=sys.stderr)
                return 1
            start, end = expand_month(args.month)
        usage = fetch_usage(args.user_id, start, end, partitions=args.partitions)
        pprint(usage)
    elif args.command == "active":
        start = args.start
        end = args.end
        if args.month:
            if args.end:
                print("--end cannot be used with --month", file=sys.stderr)
                return 1
            start, end = expand_month(args.month)
        usage = fetch_active_usage(start, end, active_users=args.active_users)
        pprint(usage)
    elif args.command == "report":
        start = args.start
        end = args.end
        if args.month:
            if args.end:
                print("--end cannot be used with --month", file=sys.stderr)
                return 1
            start, end = expand_month(args.month)
        try:
            report = create_report(
                args.user_id,
                start,
                end,
                partitions=args.partitions,
                netrc_file=args.netrc_file,
            )
        except SimAPIError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        output_path = write_report_csv(
            report,
            "output",
            f"{args.user_id}.csv",
            start=start,
            end=end,
        )

        report_with_period = report.copy()
        report_with_period["period_start"] = start
        report_with_period["period_end"] = end

        pprint(report_with_period)
        print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI execution
    raise SystemExit(main())
