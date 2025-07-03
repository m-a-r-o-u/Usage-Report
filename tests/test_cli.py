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


def test_report_active_legacy(monkeypatch):
    from usage_report import cli
    legacy = [{"user1": 1.0}]
    monkeypatch.setattr(cli, "load_month", lambda month, partitions=None: legacy)
    called = {}
    def fake_create(start, end, partitions=None, netrc_file=None):
        called['yes'] = True
        return [{"kennung": "u1"}]
    monkeypatch.setattr(cli, "create_active_reports", fake_create)
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "print_usage_table", lambda rows, *a, **k: None)
    cli.main(["report", "active", "--month", "2025-06"])
    assert called.get('yes')


def test_report_active_netrc(monkeypatch):
    from usage_report import cli

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: None)
    captured = {}

    def fake_create(start, end, partitions=None, netrc_file=None):
        captured["netrc"] = netrc_file
        return []

    monkeypatch.setattr(cli, "create_active_reports", fake_create)
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "print_usage_table", lambda rows, *a, **k: None)

    cli.main(["report", "active", "--month", "2025-06", "--netrc-file", "creds"])
    assert captured.get("netrc") == "creds"


def test_show_sort_parse():
    from usage_report.cli import parse_args

    args = parse_args([
        "report",
        "show",
        "--month",
        "2025-06",
        "--sortby",
        "last_name",
        "--desc",
    ])
    assert args.report_cmd == "show"
    assert args.month == "2025-06"
    assert args.sortby == "last_name"
    assert args.desc is True


def test_show_sort_default():
    from usage_report.cli import parse_args

    args = parse_args(["report", "show", "--month", "2025-06"])
    assert args.sortby == "gpu_hours"


def test_print_usage_table_sort(capsys):
    from usage_report.cli import print_usage_table

    rows = [
        {
            "first_name": "A",
            "last_name": "",
            "email": "",
            "kennung": "a",
            "projekt": "",
            "ai_c_group": "",
            "cpu_hours": 0.0,
            "gpu_hours": 1.0,
            "ram_gb_hours": 0.0,
            "timestamp": "",
            "period_start": "",
            "period_end": "",
        },
        {
            "first_name": "B",
            "last_name": "",
            "email": "",
            "kennung": "b",
            "projekt": "",
            "ai_c_group": "",
            "cpu_hours": 0.0,
            "gpu_hours": 5.0,
            "ram_gb_hours": 0.0,
            "timestamp": "",
            "period_start": "",
            "period_end": "",
        },
    ]

    print_usage_table(rows, sort_key="gpu_hours", reverse=True)
    out = capsys.readouterr().out.splitlines()
    first_row = out[2]
    assert first_row.startswith("B")
