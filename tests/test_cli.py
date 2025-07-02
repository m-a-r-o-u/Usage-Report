from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from usage_report.cli import expand_month


def test_expand_month_middle():
    start, end = expand_month("2025-06")
    assert start == "2025-06-01"
    assert end == "2025-06-30"


def test_expand_month_december():
    start, end = expand_month("2025-12")
    assert start == "2025-12-01"
    assert end == "2025-12-31"


def test_report_user_alias():
    from usage_report.cli import parse_args

    args = parse_args(["report", "di38qex", "--month", "2025-06"])
    assert args.command == "report"
    assert args.report_cmd == "user"
    assert args.user_id == "di38qex"
    assert args.month == "2025-06"
