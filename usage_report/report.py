"""Utilities to generate combined usage reports."""
from __future__ import annotations

from pathlib import Path
import csv

from .api import SimAPI
from .slurm import fetch_usage


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


def create_report(user_id: str, start: str, end: str | None = None, *, netrc_file: str | Path | None = None) -> dict[str, object]:
    """Return a combined report dictionary for *user_id*."""
    api = SimAPI(netrc_file=netrc_file)
    user_data = _normalize_user_data(api.fetch_user(user_id))
    usage = fetch_usage(user_id, start, end)

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
    }
    report.update(usage)
    return report


def write_report_csv(report: dict[str, object], output_dir: str | Path, filename: str) -> Path:
    """Write *report* to ``output_dir/filename`` and return the path."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(report.keys()))
        writer.writeheader()
        writer.writerow(report)
    return out_path


__all__ = ["create_report", "write_report_csv"]
