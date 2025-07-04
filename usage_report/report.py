"""Utilities to generate combined usage reports."""
from __future__ import annotations

from pathlib import Path
import csv
import logging
from datetime import datetime
from typing import Iterable

from .api import SimAPI, SimAPIError
from .slurm import fetch_usage
from .groups import list_user_groups
from .sreport import fetch_active_usage

logger = logging.getLogger(__name__)


def _normalize_user_data(data: dict[str, object]) -> dict[str, object]:
    """Return *data* with nested "daten" fields merged at the top level."""
    if not isinstance(data, dict):
        return data
    result = data.copy()
    details = result.get("daten")
    if isinstance(details, dict):
        for key, value in details.items():
            result.setdefault(key, value)
        if "emailadressen" in details and "emails" not in result:
            result["emails"] = details["emailadressen"]
    return result


def _pick_email(data: dict[str, object]) -> str:
    """Return the best email from *data*.

    Prefers an address matching ``first.last@`` if available.
    """
    first = (
        data.get("first_name")
        or data.get("firstname")
        or data.get("vorname")
    )
    last = (
        data.get("last_name")
        or data.get("lastname")
        or data.get("nachname")
    )
    preferred = f"{first}.{last}".lower() if first and last else None
    emails = (
        data.get("emails")
        or data.get("emailadressen")
        or data.get("email")
        or []
    )
    if isinstance(emails, (str, dict)):
        emails = [emails]
    for item in emails:
        if isinstance(item, dict):
            addr = item.get("address") or item.get("adresse")
        else:
            addr = item
        if not isinstance(addr, str):
            continue
        if preferred and addr.lower().startswith(preferred):
            return addr
    for item in emails:
        if isinstance(item, dict):
            addr = item.get("address") or item.get("adresse")
        else:
            addr = item
        if isinstance(addr, str):
            return addr
    return ""


def create_report(
    user_id: str,
    start: str,
    end: str | None = None,
    *,
    partitions: Iterable[str] | None = None,
    netrc_file: str | Path | None = None,
) -> dict[str, object]:
    """Return a combined report dictionary for *user_id*."""
    api = SimAPI(netrc_file=netrc_file)
    user_data = _normalize_user_data(api.fetch_user(user_id))
    usage = fetch_usage(user_id, start, end, partitions=partitions)
    groups = list_user_groups(user_id)
    ai_c_groups = [g for g in groups if g.endswith("ai-c")]
    ai_c_group = "|".join(ai_c_groups) if ai_c_groups else ""

    report = {
        "first_name": user_data.get("first_name")
        or user_data.get("firstname")
        or user_data.get("vorname"),
        "last_name": user_data.get("last_name")
        or user_data.get("lastname")
        or user_data.get("nachname"),
        "email": _pick_email(user_data),
        "kennung": user_data.get("kennung"),
        "projekt": user_data.get("projekt"),
        "ai_c_group": ai_c_group,
    }
    report.update(usage)
    return report


def create_active_reports(
    start: str,
    end: str | None = None,
    *,
    partitions: Iterable[str] | None = None,
    netrc_file: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return combined report rows for all active users.

    The list includes a ``timestamp`` as well as ``period_start`` and
    ``period_end`` fields for each user.
    """
    # fetch_active_usage does not support partition filtering via sreport,
    # so the partitions are only applied when creating individual reports
    active = fetch_active_usage(start, end)
    user_ids = [u for u in active if u != "partitions"]
    rows: list[dict[str, object]] = []
    for user in user_ids:
        try:
            report = create_report(
                user,
                start,
                end,
                partitions=partitions,
                netrc_file=netrc_file,
            )
        except SimAPIError as exc:
            logger.error("Skipping user %s due to error: %s", user, exc)
            continue
        report["period_start"] = start
        report["period_end"] = end
        report["timestamp"] = datetime.now().isoformat(timespec="seconds")
        rows.append(report)
    return rows


def enrich_report_rows(
    rows: Iterable[dict[str, object]], *, netrc_file: str | Path | None = None
) -> list[dict[str, object]]:
    """Return ``rows`` with missing user information filled via SIM API."""

    api = SimAPI(netrc_file=netrc_file)
    enriched: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue
        if all(row.get(key) for key in ("first_name", "last_name", "email", "projekt")):
            enriched.append(row)
            continue
        user_id = row.get("kennung")
        if not user_id:
            enriched.append(row)
            continue
        try:
            data = _normalize_user_data(api.fetch_user(str(user_id)))
        except SimAPIError:
            enriched.append(row)
            continue
        groups = list_user_groups(str(user_id))
        ai_c_groups = [g for g in groups if g.endswith("ai-c")]
        ai_c_group = "|".join(ai_c_groups) if ai_c_groups else ""

        new = row.copy()
        new.setdefault(
            "first_name",
            data.get("first_name") or data.get("firstname") or data.get("vorname"),
        )
        new.setdefault(
            "last_name",
            data.get("last_name") or data.get("lastname") or data.get("nachname"),
        )
        new.setdefault("email", _pick_email(data))
        new.setdefault("projekt", data.get("projekt"))
        new.setdefault("ai_c_group", ai_c_group)
        enriched.append(new)
    return enriched


def write_report_csv(
    report: dict[str, object],
    output_dir: str | Path,
    filename: str,
    *,
    start: str | None = None,
    end: str | None = None,
    partitions: Iterable[str] | None = None,
) -> Path:
    """Write *report* to ``output_dir/filename`` and return the path.

    If the file already exists, the row is appended.  A ``timestamp`` as well
    as ``period_start`` and ``period_end`` columns are added automatically.
    The ``partitions`` column records which partitions were included in the
    calculation, joined by commas.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    row = report.copy()
    row["timestamp"] = datetime.now().isoformat(timespec="seconds")
    row["period_start"] = start
    row["period_end"] = end or ""
    row["partitions"] = ",".join(sorted(partitions or []))

    if out_path.exists():
        with out_path.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or list(row.keys())
        with out_path.open("a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writerow({f: row.get(f, "") for f in fieldnames})
    else:
        fieldnames = list(row.keys())
        with out_path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)
    return out_path


def aggregate_rows(
    rows: Iterable[dict[str, object]],
    *,
    by_group: bool = False,
    partitions: Iterable[str] | None = None,
) -> list[dict[str, object]]:
    """Return ``rows`` aggregated either by user or by ``ai_c_group``."""

    part_str = ",".join(sorted(partitions or []))
    aggr: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        groups = row.get("ai_c_group", "")
        keys = [row.get("kennung")] if not by_group else (groups.split("|") if groups else [""])
        for key in keys:
            if key is None:
                continue
            cur = aggr.setdefault(
                str(key),
                {
                    "first_name": row.get("first_name"),
                    "last_name": row.get("last_name"),
                    "email": row.get("email"),
                    "kennung": row.get("kennung"),
                    "projekt": row.get("projekt"),
                    "ai_c_group": key if by_group else row.get("ai_c_group", ""),
                    "cpu_hours": 0.0,
                    "gpu_hours": 0.0,
                    "ram_gb_hours": 0.0,
                    "timestamp": row.get("timestamp", ""),
                    "period_start": row.get("period_start"),
                    "period_end": row.get("period_end"),
                    "partition": part_str,
                },
            )
            cur["cpu_hours"] = float(cur.get("cpu_hours", 0.0)) + float(row.get("cpu_hours", 0.0))
            cur["gpu_hours"] = float(cur.get("gpu_hours", 0.0)) + float(row.get("gpu_hours", 0.0))
            cur["ram_gb_hours"] = float(cur.get("ram_gb_hours", 0.0)) + float(row.get("ram_gb_hours", 0.0))

            start = str(row.get("period_start")) if row.get("period_start") else ""
            end = str(row.get("period_end")) if row.get("period_end") else ""
            if cur.get("period_start") is None or (start and start < cur["period_start"]):
                cur["period_start"] = start
            if cur.get("period_end") is None or (end and end > cur["period_end"]):
                cur["period_end"] = end
    return list(aggr.values())


__all__ = [
    "create_report",
    "create_active_reports",
    "enrich_report_rows",
    "write_report_csv",
    "aggregate_rows",
]
