"""Command line interface for usage."""
from __future__ import annotations

import argparse
import sys
from pprint import pprint
from datetime import datetime, timedelta
import logging

from .api import SimAPI, SimAPIError
from .slurm import fetch_usage
from .sreport import fetch_active_usage
from .database import store_month, list_months, load_month
from .report import (
    create_report,
    create_active_reports,
    enrich_report_rows,
    write_report_csv,
)


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


def print_usage_table(
    rows: list[dict[str, object]],
    *,
    start: str | None = None,
    end: str | None = None,
    sort_key: str | None = None,
    reverse: bool = False,
) -> None:
    """Print ``rows`` as a table."""
    if start or end:
        period = f"{start or '?'} - {end or '?'}"
        print(f"Period: {period}")
    if not rows:
        print("No data")
        return

    columns = [
        "first_name",
        "last_name",
        "email",
        "kennung",
        "projekt",
        "ai_c_group",
        "cpu_hours",
        "gpu_hours",
        "ram_gb_hours",
        "timestamp",
        "period_start",
        "period_end",
    ]

    widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            val = row.get(c, "")
            if isinstance(val, float):
                val = f"{val:.1f}"
            widths[c] = max(widths[c], len(str(val)))

    if sort_key:
        try:
            rows = sorted(rows, key=lambda r: r.get(sort_key) or 0, reverse=reverse)
        except TypeError:
            rows = sorted(
                rows,
                key=lambda r: str(r.get(sort_key, "")),
                reverse=reverse,
            )

    header = " ".join(f"{c:<{widths[c]}}" for c in columns)
    print(header)
    print("-" * len(header))
    for row in rows:
        parts = []
        for c in columns:
            val = row.get(c, "")
            if isinstance(val, float):
                parts.append(f"{val:>{widths[c]}.1f}")
            else:
                parts.append(f"{str(val):<{widths[c]}}")
        print(" ".join(parts))


def print_report_table(report: dict[str, object]) -> None:
    """Print ``report`` dictionary as a single-row table."""
    if not report:
        print("No data")
        return
    print_usage_table([report])


def _add_sim_parser(sub: argparse._SubParsersAction) -> None:
    sim_parser = sub.add_parser("sim", help="Fetch LRZ SIM API user info")
    sim_parser.add_argument("user_id", help="LRZ user identifier")
    sim_parser.add_argument(
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
    report_parser = sub.add_parser("report", help="Generate reports")
    rep_sub = report_parser.add_subparsers(dest="report_cmd", required=True)

    user_parser = rep_sub.add_parser("user", help="Generate combined report for a user")
    user_parser.add_argument("user_id", help="LRZ user identifier")
    grp_u = user_parser.add_mutually_exclusive_group(required=True)
    grp_u.add_argument("-S", "--start", dest="start", help="Start date YYYY-MM-DD")
    grp_u.add_argument("--month", help="Month YYYY-MM")
    user_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    user_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )
    user_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )

    active_parser = rep_sub.add_parser("active", help="Usage report for active users")
    grp_a = active_parser.add_mutually_exclusive_group(required=True)
    grp_a.add_argument("-S", "--start", dest="start", help="Start date YYYY-MM-DD")
    grp_a.add_argument("--month", help="Month YYYY-MM")
    active_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    active_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )
    active_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )
    active_parser.add_argument(
        "--sortby",
        dest="sortby",
        default="gpu_hours",
        help="Column to sort by when showing cached data (default: gpu_hours)",
    )
    active_parser.add_argument(
        "--desc",
        action="store_true",
        help="Sort in descending order when showing cached data",
    )

    list_parser = rep_sub.add_parser("list", help="List stored monthly usage data")

    show_parser = rep_sub.add_parser("show", help="Show stored monthly usage")
    show_parser.add_argument("--month", required=True, help="Month YYYY-MM")
    show_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition filter used during storage",
    )
    show_parser.add_argument(
        "--netrc-file",
        dest="netrc_file",
        help="Custom path to .netrc file for authentication",
    )
    show_parser.add_argument(
        "--sortby",
        dest="sortby",
        default="gpu_hours",
        help="Column to sort by (default: gpu_hours)",
    )
    show_parser.add_argument(
        "--desc",
        action="store_true",
        help="Sort in descending order",
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
        help="Active user identifier (can be used multiple times)",
    )
    active_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    debug = False
    while "--debug" in argv_list:
        argv_list.remove("--debug")
        debug = True
    if argv_list and argv_list[0] == "report":
        if (
            len(argv_list) > 1
            and not argv_list[1].startswith("-")
            and argv_list[1] not in {"user", "active", "list", "show"}
        ):
            argv_list.insert(1, "user")

    parser = argparse.ArgumentParser(description="Usage reporting utilities")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_sim_parser(sub)
    _add_slurm_parser(sub)
    _add_report_parser(sub)
    _add_active_parser(sub)
    args = parser.parse_args(argv_list)
    if debug:
        args.debug = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if getattr(args, "debug", False):
        logging.basicConfig(level=logging.DEBUG)
    if args.command == "sim":
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
        usage = fetch_active_usage(start, end, active_users=args.active_users, partitions=args.partitions)
        pprint(usage)
    elif args.command == "report":
        if args.report_cmd == "user":
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
                partitions=args.partitions,
            )

            report_with_period = report.copy()
            report_with_period["period_start"] = start
            report_with_period["period_end"] = end

            print_report_table(report_with_period)
            print(f"Report written to {output_path}")
        elif args.report_cmd == "active":
            start = args.start
            end = args.end
            if args.month:
                if args.end:
                    print("--end cannot be used with --month", file=sys.stderr)
                    return 1
                start, end = expand_month(args.month)
            existing = None
            if args.month:
                existing = load_month(args.month, partitions=args.partitions)
            if existing is not None:
                rows = list(existing)
                sample = rows[0] if rows else {}
                if not isinstance(sample, dict) or "kennung" not in sample:
                    rows = create_active_reports(
                        start,
                        end,
                        partitions=args.partitions,
                        netrc_file=args.netrc_file,
                    )
                    if args.month:
                        store_month(
                            args.month,
                            start,
                            end or "",
                            rows,
                            partitions=args.partitions,
                        )
                else:
                    rows = enrich_report_rows(rows, netrc_file=args.netrc_file)
                print_usage_table(
                    rows,
                    sort_key=args.sortby,
                    reverse=(args.desc or args.sortby == "gpu_hours"),
                )
            else:
                rows = create_active_reports(
                    start,
                    end,
                    partitions=args.partitions,
                    netrc_file=args.netrc_file,
                )
                print_usage_table(rows)

                if args.month:
                    store_month(
                        args.month,
                        start,
                        end or "",
                        rows,
                        partitions=args.partitions,
                    )
        elif args.report_cmd == "list":
            entries = list_months()
            pprint(entries)
        elif args.report_cmd == "show":
            parts = args.partitions
            entries = [e for e in list_months() if e["month"] == args.month]
            if parts is None:
                if len(entries) == 1:
                    parts = entries[0]["partitions"].split(",") if entries[0]["partitions"] else []
                elif len(entries) > 1:
                    for ent in entries:
                        data = load_month(
                            args.month,
                            partitions=ent["partitions"].split(",") if ent["partitions"] else [],
                        ) or []
                        print_usage_table(
                            data,
                            start=ent["start"],
                            end=ent["end"],
                        )
                    if not entries:
                        print_usage_table([])
                    return 0
            usage = load_month(args.month, partitions=parts) or []
            usage = enrich_report_rows(usage, netrc_file=args.netrc_file)
            match = next(
                (e for e in entries if e["partitions"] == ",".join(sorted(parts or []))),
                None,
            )
            start = match["start"] if match else None
            end = match["end"] if match else None
            print_usage_table(
                usage,
                start=start,
                end=end,
                sort_key=args.sortby,
                reverse=(args.desc or args.sortby == "gpu_hours"),
            )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI execution
    raise SystemExit(main())
