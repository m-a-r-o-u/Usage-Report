"""Utilities for parsing Slurm accounting data via ``sacct``."""
from __future__ import annotations

import subprocess
from typing import Iterable, Dict
import fnmatch


def parse_elapsed(elapsed: str) -> float:
    """Convert an elapsed time string to hours."""
    days = 0
    if "-" in elapsed:
        day_str, time_str = elapsed.split("-", 1)
        days = int(day_str)
    else:
        time_str = elapsed
    hours, minutes, seconds = map(int, time_str.split(":"))
    return days * 24 + hours + minutes / 60 + seconds / 3600


def parse_mem(mem: str) -> float:
    """Return memory in gigabytes from a Slurm memory string."""
    units = {"K": 1 / 1024 / 1024, "M": 1 / 1024, "G": 1, "T": 1024}
    if mem and mem[-1].isalpha():
        value = float(mem[:-1])
        unit = mem[-1].upper()
    else:
        value = float(mem or 0)
        unit = "M"
    return value * units.get(unit, 0)


def parse_tres(tres: str) -> Dict[str, str]:
    """Parse a TRES string like ``cpu=1,mem=4G`` into a dictionary."""
    result: Dict[str, str] = {}
    for item in tres.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
    return result


def parse_sacct_output(text: str) -> Iterable[Dict[str, str]]:
    """Yield dictionaries for each line in ``sacct`` ``--parsable2`` output."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("|")
    for line in lines[1:]:
        values = line.split("|")
        yield dict(zip(header, values))


def fetch_usage(
    user: str,
    start: str,
    end: str | None = None,
    *,
    partitions: Iterable[str] | None = None,
) -> dict[str, float]:
    """Return aggregated GPU/CPU/RAM hours for *user* between *start* and *end*.

    Parameters
    ----------
    user:
        User identifier to query.
    start:
        Start date in ``YYYY-MM-DD`` format.
    end:
        Optional end date in ``YYYY-MM-DD`` format.
    """
    cmd = [
        "sacct",
        "-u",
        user,
        "--format=JobID,Partition,Elapsed,NCPUS,AllocTRES",
        "--parsable2",
        "-S",
        start,
    ]
    if end:
        cmd.extend(["-E", end])

    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    cpu_h = gpu_h = ram_h = 0.0
    for rec in parse_sacct_output(proc.stdout):
        job_id = rec.get("JobID", "")
        if "." in job_id:
            # skip job steps to avoid double counting
            continue
        if partitions:
            part = rec.get("Partition", "")
            if not any(fnmatch.fnmatch(part, pat) for pat in partitions):
                continue
        elapsed_h = parse_elapsed(rec.get("Elapsed", "0:0:0"))
        cpus = int(rec.get("NCPUS", "0"))
        tres = parse_tres(rec.get("AllocTRES", ""))
        gpus = int(tres.get("gres/gpu", tres.get("gpu", "0")).split("(")[0] or 0)
        mem_gb = parse_mem(tres.get("mem", "0"))
        cpu_h += cpus * elapsed_h
        gpu_h += gpus * elapsed_h
        ram_h += mem_gb * elapsed_h
    return {"cpu_hours": cpu_h, "gpu_hours": gpu_h, "ram_gb_hours": ram_h}
