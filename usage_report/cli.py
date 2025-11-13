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
    aggregate_rows,
    sum_rows,
)
from .plotting import create_donut_plot


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


def _parse_plot_spec(spec: str) -> tuple[str, str]:
    """Return (kind, column) parsed from *spec*."""
    parts = [p.strip() for p in spec.split(',')]
    if len(parts) != 2:
        raise ValueError("plot spec must be type,column")
    kind = parts[0].lower()
    column = parts[1]
    return kind, column


def print_usage_table(
    rows: list[dict[str, object]],
    *,
    start: str | None = None,
    end: str | None = None,
    sort_key: str | None = None,
    reverse: bool = False,
    columns: list[str] | None = None,
) -> None:
    """Print ``rows`` as a table."""
    if start or end:
        period = f"{start or '?'} - {end or '?'}"
        print(f"Period: {period}")
    if not rows:
        print("No data")
        return

    if columns is None:
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
    slurm_parser.add_argument(
        "user_specs",
        nargs="+",
        help="LRZ user identifier(s); accepts comma separated values",
    )
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
        "--aggregate",
        nargs="?",
        const="user",
        choices=["user", "groups", "all"],
        help="Aggregate cached months (optionally by group)",
    )
    active_parser.add_argument(
        "--plot",
        dest="plot",
        help="Create a plot from aggregated data (e.g. donut,gpu_hours)",
    )
    active_parser.add_argument(
        "--ignore_user",
        dest="ignore_user",
        help="Comma separated list of user IDs to ignore when aggregating",
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
    grp.add_argument("--month", help="Month YYYY-MM or comma separated months")
    active_parser.add_argument("-E", "--end", help="End date YYYY-MM-DD")
    active_parser.add_argument(
        "-u",
        "--user",
        dest="active_users",
        action="append",
        help="Active user identifier (can be used multiple times)",
    )
    active_parser.add_argument(
        "--user-list",
        dest="active_user_list",
        help="Comma separated list of active user identifiers",
    )
    active_parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Partition to include (can be used multiple times, supports wildcards)",
    )
    active_parser.add_argument(
        "--aggregate",
        nargs="?",
        const="user",
        choices=["user", "groups", "all"],
        help="Aggregate cached months (optionally by group)",
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
    if getattr(args, "ignore_user", None):
        args.ignore_user = [
            u.strip() for u in str(args.ignore_user).split(",") if u.strip()
        ]
    if getattr(args, "command", None) == "slurm":
        raw_specs = getattr(args, "user_specs", [])
        users: list[str] = []
        for spec in raw_specs:
            parts = [part.strip() for part in spec.split(",") if part.strip()]
            users.extend(parts)
        seen: set[str] = set()
        deduped: list[str] = []
        for user in users:
            if user not in seen:
                seen.add(user)
                deduped.append(user)
        args.users = deduped
    if getattr(args, "active_user_list", None):
        parsed_users = [
            u.strip()
            for u in str(args.active_user_list).split(",")
            if u.strip()
        ]
        combined = list(args.active_users or []) + parsed_users
        seen: set[str] = set()
        deduped: list[str] = []
        for user in combined:
            if user not in seen:
                seen.add(user)
                deduped.append(user)
        args.active_users = deduped or None
    elif getattr(args, "active_users", None):
        seen: set[str] = set()
        deduped = []
        for user in args.active_users:
            if user not in seen:
                seen.add(user)
                deduped.append(user)
        args.active_users = deduped or None
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
        users = getattr(args, "users", [])
        if not users:
            print("At least one user must be specified", file=sys.stderr)
            return 1
        if len(users) == 1:
            usage = fetch_usage(users[0], start, end, partitions=args.partitions)
            pprint(usage)
        else:
            per_user: list[dict[str, object]] = []
            totals = {"cpu_hours": 0.0, "gpu_hours": 0.0, "ram_gb_hours": 0.0}
            for user in users:
                usage = fetch_usage(user, start, end, partitions=args.partitions)
                per_user.append({"user": user, **usage})
                for key in totals:
                    totals[key] += float(usage.get(key, 0.0))
            result = {"users": per_user, "group_usage": totals}
            pprint(result)
    elif args.command == "active":
        start = args.start
        end = args.end
        if args.month:
            if args.end:
                print("--end cannot be used with --month", file=sys.stderr)
                return 1
            start, end = expand_month(args.month)
        usage = fetch_active_usage(start, end, active_users=args.active_users, partitions=args.partitions)
        if args.active_users:
            partitions = usage.get("partitions") if isinstance(usage, dict) else []
            users_usage = []
            for user in args.active_users:
                value = 0.0
                if isinstance(usage, dict):
                    try:
                        value = float(usage.get(user, 0.0))
                    except (TypeError, ValueError):
                        value = 0.0
                users_usage.append({"user": user, "hours": value})
            group_hours = sum(item["hours"] for item in users_usage)
            result = {
                "partitions": partitions,
                "users": users_usage,
                "group_hours": group_hours,
            }
            pprint(result)
        else:
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
            months = [args.month] if args.month and "," not in args.month else []
            if args.month and "," in args.month:
                months = [m.strip() for m in args.month.split(",") if m.strip()]
            if months:
                if args.end:
                    print("--end cannot be used with --month", file=sys.stderr)
                    return 1
            agg_rows: list[dict[str, object]] = []
            if months:
                for mon in months:
                    m_start, m_end = expand_month(mon)
                    existing = load_month(mon, partitions=args.partitions)
                    if existing is not None:
                        rows = list(existing)
                        sample = rows[0] if rows else {}
                        if not isinstance(sample, dict) or "kennung" not in sample:
                            rows = create_active_reports(
                                m_start,
                                m_end,
                                partitions=args.partitions,
                                netrc_file=args.netrc_file,
                            )
                            store_month(
                                mon,
                                m_start,
                                m_end or "",
                                rows,
                                partitions=args.partitions,
                            )
                        else:
                            rows = enrich_report_rows(rows, netrc_file=args.netrc_file)
                            if args.aggregate:
                                if args.aggregate == "all":
                                    ag = sum_rows(
                                        rows,
                                        partitions=args.partitions,
                                        ignore_users=args.ignore_user,
                                    )
                                    ag["month"] = mon
                                    ag["period_start"] = m_start
                                    ag["period_end"] = m_end
                                    agg_rows.append(ag)
                                else:
                                    agg_rows.extend(rows)
                            else:
                                part_val = ",".join(sorted(args.partitions or ["*"]))
                                show_rows = [r | {"partition": part_val} for r in rows]
                                cols = [
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
                                    "partition",
                                ]
                                print_usage_table(
                                    show_rows,
                                    sort_key=args.sortby,
                                    reverse=(args.desc or args.sortby == "gpu_hours"),
                                    columns=cols,
                                )
                    else:
                        rows = create_active_reports(
                            m_start,
                            m_end,
                            partitions=args.partitions,
                            netrc_file=args.netrc_file,
                        )
                        store_month(
                            mon,
                            m_start,
                            m_end or "",
                            rows,
                            partitions=args.partitions,
                        )
                        if args.aggregate:
                            if args.aggregate == "all":
                                ag = sum_rows(
                                    rows,
                                    partitions=args.partitions,
                                    ignore_users=args.ignore_user,
                                )
                                ag["month"] = mon
                                ag["period_start"] = m_start
                                ag["period_end"] = m_end
                                agg_rows.append(ag)
                            else:
                                agg_rows.extend(rows)
            else:
                rows = create_active_reports(
                    start,
                    end,
                    partitions=args.partitions,
                    netrc_file=args.netrc_file,
                )
                part_val = ",".join(sorted(args.partitions or ["*"]))
                show_rows = [r | {"partition": part_val} for r in rows]
                cols = [
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
                    "partition",
                ]
                print_usage_table(show_rows, columns=cols)
                if args.month:
                    store_month(
                        args.month,
                        start,
                        end or "",
                        rows,
                        partitions=args.partitions,
                    )
                if args.aggregate:
                    if args.aggregate == "all":
                        ag = sum_rows(
                            rows,
                            partitions=args.partitions,
                            ignore_users=args.ignore_user,
                        )
                        ag["period_start"] = start
                        ag["period_end"] = end
                        ag["month"] = args.month or ""
                        agg_rows.append(ag)
                    else:
                        agg_rows.extend(rows)

            if args.aggregate and agg_rows:
                if args.aggregate == "all":
                    aggregated = agg_rows
                    cols = [
                        "month",
                        "partition",
                        "cpu_hours",
                        "gpu_hours",
                        "ram_gb_hours",
                        "timestamp",
                        "period_start",
                        "period_end",
                    ]
                    print_usage_table(
                        aggregated,
                        sort_key=args.sortby,
                        reverse=(args.desc or args.sortby == "gpu_hours"),
                        columns=cols,
                    )
                else:
                    aggregated = aggregate_rows(
                        agg_rows,
                        by_group=(args.aggregate == "groups"),
                        partitions=args.partitions,
                        ignore_users=args.ignore_user,
                    )
                    if args.aggregate == "groups":
                        cols = [
                            "ai_c_group",
                            "partition",
                            "cpu_hours",
                            "gpu_hours",
                            "ram_gb_hours",
                            "timestamp",
                            "period_start",
                            "period_end",
                        ]
                    else:
                        cols = [
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
                            "partition",
                        ]
                    print_usage_table(
                        aggregated,
                        sort_key=args.sortby,
                        reverse=(args.desc or args.sortby == "gpu_hours"),
                        columns=cols,
                    )
                    if args.plot:
                        kind, column = _parse_plot_spec(args.plot)
                        if kind == "donut":
                            if aggregated:
                                start_p = min(
                                    r.get("period_start") or "" for r in aggregated
                                )
                                end_p = max(
                                    r.get("period_end") or "" for r in aggregated
                                )
                            else:
                                start_p = end_p = None
                            create_donut_plot(
                                aggregated,
                                column,
                                start=start_p or None,
                                end=end_p or None,
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
