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


def test_active_sort_parse():
    from usage_report.cli import parse_args

    args = parse_args([
        "report",
        "active",
        "--month",
        "2025-06",
        "--sortby",
        "last_name",
        "--desc",
    ])
    assert args.sortby == "last_name"
    assert args.desc is True


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


def test_report_active_sort(monkeypatch):
    from usage_report import cli

    data = [{"kennung": "u1", "gpu_hours": 1.0}]
    monkeypatch.setattr(cli, "load_month", lambda *a, **k: data)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)

    captured = {}

    def fake_print(rows, *a, **kw):
        captured.update(kw)

    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)
    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main([
        "report",
        "active",
        "--month",
        "2025-06",
        "--sortby",
        "last_name",
        "--desc",
    ])

    assert captured.get("sort_key") == "last_name"
    assert captured.get("reverse") is True


def test_report_active_sort_ignore(monkeypatch):
    from usage_report import cli

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: None)

    called = {}

    def fake_create(start, end, partitions=None, netrc_file=None):
        called["created"] = True
        return []

    monkeypatch.setattr(cli, "create_active_reports", fake_create)
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)

    captured = {}

    def fake_print(rows, *a, **kw):
        captured.update(kw)

    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main([
        "report",
        "active",
        "--month",
        "2025-06",
        "--sortby",
        "last_name",
    ])

    assert "created" in called
    assert captured.get("sort_key") is None


def test_parse_multi_month_aggregate():
    from usage_report.cli import parse_args

    args = parse_args([
        "report",
        "active",
        "--month",
        "2025-05,2025-06",
        "--aggregate",
        "group",
    ])

    assert args.month == "2025-05,2025-06"
    assert args.aggregate == "group"


def test_active_aggregate(monkeypatch):
    from usage_report import cli

    months = {
        "2025-05": [
            {
                "kennung": "u1",
                "cpu_hours": 1.0,
                "gpu_hours": 1.0,
                "ram_gb_hours": 1.0,
                "timestamp": "t1",
                "period_start": "2025-05-01",
                "period_end": "2025-05-31",
            }
        ],
        "2025-06": [
            {
                "kennung": "u1",
                "cpu_hours": 2.0,
                "gpu_hours": 0.5,
                "ram_gb_hours": 0.0,
                "timestamp": "t2",
                "period_start": "2025-06-01",
                "period_end": "2025-06-30",
            }
        ],
    }

    monkeypatch.setattr(cli, "load_month", lambda m, partitions=None: months[m])
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)

    captured = {}

    def fake_print(rows, *a, **k):
        captured["rows"] = rows

    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main(["report", "active", "--month", "2025-05,2025-06", "--aggregate"])

    row = captured["rows"][0]
    assert row["cpu_hours"] == 3.0
    assert row["gpu_hours"] == 1.5
    assert row["partition"] == "*"


def test_active_aggregate_group(monkeypatch):
    from usage_report import cli
    sample = [
        {
            "kennung": "u1",
            "ai_c_group": "g1",
            "cpu_hours": 1.0,
            "gpu_hours": 1.0,
            "ram_gb_hours": 1.0,
            "timestamp": "t",
            "period_start": "2025-06-01",
            "period_end": "2025-06-30",
        }
    ]

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: sample)
    called = {}

    def fake_aggregate(rows, *, by_group, partitions=None):
        called["group"] = by_group
        return []

    monkeypatch.setattr(cli, "aggregate_rows", fake_aggregate)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)
    monkeypatch.setattr(cli, "print_usage_table", lambda *a, **k: None)

    cli.main(["report", "active", "--month", "2025-06", "--aggregate", "group"])

    assert called.get("group") is True


def test_active_aggregate_group_sort(monkeypatch):
    from usage_report import cli

    sample = [
        {
            "kennung": "u1",
            "ai_c_group": "g1",
            "cpu_hours": 1.0,
            "gpu_hours": 2.0,
            "ram_gb_hours": 0.0,
            "timestamp": "t",
            "period_start": "2025-06-01",
            "period_end": "2025-06-30",
        }
    ]

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: sample)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)

    monkeypatch.setattr(cli, "aggregate_rows", lambda *a, **k: sample)

    captured = {}

    def fake_print(rows, *a, **kw):
        captured.update(kw)

    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main([
        "report",
        "active",
        "--month",
        "2025-06",
        "--aggregate",
        "group",
        "--sortby",
        "gpu_hours",
    ])

    assert captured.get("sort_key") == "gpu_hours"
    assert captured.get("reverse") is True


def test_active_output_partition(monkeypatch):
    from usage_report import cli

    sample = [
        {
            "kennung": "u1",
            "cpu_hours": 1.0,
            "gpu_hours": 1.0,
            "ram_gb_hours": 0.0,
            "timestamp": "t",
            "period_start": "2025-06-01",
            "period_end": "2025-06-30",
        }
    ]

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: sample)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)

    captured = {}

    def fake_print(rows, *a, **kw):
        captured["rows"] = rows
        captured["cols"] = kw.get("columns")

    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main(["report", "active", "--month", "2025-06", "--partition", "mcml*"])

    row = captured["rows"][0]
    assert row["partition"] == "mcml*"
    assert "partition" in captured["cols"]


def test_active_output_partition_all(monkeypatch):
    from usage_report import cli

    sample = [{"kennung": "u1"}]

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: sample)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)

    captured = {}

    def fake_print(rows, *a, **kw):
        captured["rows"] = rows
        captured["cols"] = kw.get("columns")

    monkeypatch.setattr(cli, "print_usage_table", fake_print)

    cli.main(["report", "active", "--month", "2025-06"])

    row = captured["rows"][0]
    assert row["partition"] == "*"
    assert "partition" in captured["cols"]


def test_parse_plot_option():
    from usage_report.cli import parse_args

    args = parse_args([
        "report",
        "active",
        "--month",
        "2025-06",
        "--aggregate",
        "group",
        "--plot",
        "donut,gpu_hours",
    ])

    assert args.plot == "donut,gpu_hours"


def test_active_plot_call(monkeypatch):
    from usage_report import cli

    sample = [
        {
            "kennung": "u1",
            "ai_c_group": "g",
            "gpu_hours": 5.0,
            "cpu_hours": 0.0,
            "ram_gb_hours": 0.0,
            "timestamp": "t",
            "period_start": "p1",
            "period_end": "p2",
        }
    ]

    monkeypatch.setattr(cli, "load_month", lambda *a, **k: sample)
    monkeypatch.setattr(cli, "create_active_reports", lambda *a, **k: [])
    monkeypatch.setattr(cli, "store_month", lambda *a, **k: None)
    monkeypatch.setattr(cli, "enrich_report_rows", lambda r, **k: r)
    monkeypatch.setattr(cli, "aggregate_rows", lambda *a, **k: sample)
    monkeypatch.setattr(cli, "print_usage_table", lambda *a, **k: None)

    called = {}

    def fake_plot(rows, column, *, start=None, end=None, title=None):
        called["column"] = column
        called["start"] = start
        called["end"] = end

    monkeypatch.setattr(cli, "create_donut_plot", fake_plot)

    cli.main([
        "report",
        "active",
        "--month",
        "2025-06",
        "--aggregate",
        "group",
        "--plot",
        "donut,gpu_hours",
    ])

    assert called["column"] == "gpu_hours"
    assert called["start"] == "p1"
    assert called["end"] == "p2"
