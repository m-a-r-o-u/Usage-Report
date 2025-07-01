from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from usage_report.database import store_month, load_month, list_months


def test_store_and_load_month(tmp_path):
    db = tmp_path / "test.db"
    usage = {"user1": 10.0}
    store_month("2025-06", "2025-06-01", "2025-06-30", usage, partitions=["gpu"], db_path=db)
    result = load_month("2025-06", partitions=["gpu"], db_path=db)
    assert result == usage
    entries = list_months(db_path=db)
    assert entries[0]["month"] == "2025-06"
