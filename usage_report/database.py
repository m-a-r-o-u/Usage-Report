import json
import sqlite3
from pathlib import Path
from typing import Iterable, Dict, Any, List


DEFAULT_DB_PATH = Path("output/usage.db")


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_usage (
            month TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            partitions TEXT NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (month, partitions)
        )
        """
    )
    conn.commit()
    conn.close()


def store_month(
    month: str,
    start: str,
    end: str,
    usage: Iterable[Dict[str, Any]],
    *,
    partitions: Iterable[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Store *usage* for *month* in the database."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    parts = ",".join(sorted(partitions or []))
    data = json.dumps(list(usage))
    conn.execute(
        "REPLACE INTO monthly_usage (month, start, end, partitions, data) VALUES (?, ?, ?, ?, ?)",
        (month, start, end, parts, data),
    )
    conn.commit()
    conn.close()


def load_month(
    month: str,
    *,
    partitions: Iterable[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]] | None:
    """Return stored usage for *month* or ``None`` if not found."""
    init_db(db_path)
    parts = ",".join(sorted(partitions or []))
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT data FROM monthly_usage WHERE month=? AND partitions=?",
        (month, parts),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def list_months(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Return a list of all stored months."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT month, start, end, partitions FROM monthly_usage ORDER BY month"
    )
    rows = [
        {"month": r[0], "start": r[1], "end": r[2], "partitions": r[3]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows
