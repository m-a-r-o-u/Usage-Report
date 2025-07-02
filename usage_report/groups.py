from __future__ import annotations

import subprocess
import sys
from typing import List


def list_user_groups(user: str) -> List[str]:
    """Return the list of groups *user* belongs to using ``id`` command."""
    try:
        proc = subprocess.run(
            ["id", user], capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as exc:
        msg = " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd)
        print(f"Error running '{msg}': {exc}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return []
    output = proc.stdout.strip()
    try:
        groups_part = output.split(" groups=", 1)[1]
    except IndexError:
        return []
    groups = []
    for item in groups_part.split(','):
        if '(' in item and ')' in item:
            start = item.find('(') + 1
            end = item.find(')', start)
            groups.append(item[start:end])
    return groups
