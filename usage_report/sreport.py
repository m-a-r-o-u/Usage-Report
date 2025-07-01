"""Utilities for fetching Slurm usage summaries via ``sreport``."""
from __future__ import annotations

import subprocess
from typing import Iterable, Dict


def parse_sreport_output(text: str) -> Dict[str, float]:
    """Return a mapping of ``user`` -> ``used hours`` from ``sreport`` output."""
    result: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("login"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        user, used = parts[0], parts[-1]
        try:
            result[user] = float(used)
        except ValueError:
            continue
    return result


def fetch_active_usage(
    start: str,
    end: str | None = None,
    *,
    active_users: Iterable[str],
) -> Dict[str, float]:
    """Return usage hours for ``active_users`` between ``start`` and ``end``.

    Parameters
    ----------
    start:
        Start date in ``YYYY-MM-DD`` format.
    end:
        Optional end date in ``YYYY-MM-DD`` format.
    active_users:
        Iterable of user identifiers to include.
    """
    cmd = [
        "sreport",
        "cluster",
        "UserUtilizationByAccount",
        f"start={start}",
    ]
    if end:
        cmd.append(f"end={end}")
    cmd.append("format=Login,Used")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    usage = parse_sreport_output(proc.stdout)
    return {u: usage.get(u, 0.0) for u in active_users}


__all__ = ["fetch_active_usage", "parse_sreport_output"]
