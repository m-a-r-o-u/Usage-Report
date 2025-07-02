from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from usage_report.database import store_month, load_month, list_months


def test_store_and_load_month(tmp_path):
    db = tmp_path / "test.db"
    row = {
        "first_name": "A",
        "last_name": "B",
        "email": "a@example.com",
        "kennung": "user1",
        "projekt": "proj",
        "ai_c_group": "",
        "cpu_hours": 10.0,
        "gpu_hours": 0.0,
        "ram_gb_hours": 0.0,
        "timestamp": "ts",
        "period_start": "2025-06-01",
        "period_end": "2025-06-30",
    }
    usage = [row]
    store_month("2025-06", "2025-06-01", "2025-06-30", usage, partitions=["gpu"], db_path=db)
    result = load_month("2025-06", partitions=["gpu"], db_path=db)
    assert result == usage
    entries = list_months(db_path=db)
    assert entries[0]["month"] == "2025-06"


def test_load_month_single_row(tmp_path):
    db = tmp_path / "test.db"
    row = {"first_name": "A", "last_name": "B"}
    from usage_report.database import init_db
    import sqlite3, json

    init_db(db_path=db)
    conn = sqlite3.connect(db)
    conn.execute(
        "REPLACE INTO monthly_usage (month, start, end, partitions, data) VALUES (?, ?, ?, ?, ?)",
        ("2025-07", "2025-07-01", "2025-07-31", "", json.dumps(row)),
    )
    conn.commit()
    conn.close()

    result = load_month("2025-07", db_path=db)
    assert result == [row]
