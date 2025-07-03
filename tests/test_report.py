from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from unittest import mock

from usage_report.report import (
    create_report,
    create_active_reports,
    enrich_report_rows,
    _pick_email,
    write_report_csv,
)
from usage_report.api import SimAPIError


def test_pick_email_preferred():
    data = {
        "vorname": "Max",
        "nachname": "Mustermann",
        "emailadressen": [
            {"adresse": "max.mustermann@example.com"},
            {"adresse": "other@example.com"},
        ],
    }
    assert _pick_email(data) == "max.mustermann@example.com"


def test_create_report(tmp_path):
    user_info = {
        "kennung": "mm123",
        "projekt": "proj",
        "daten": {
            "vorname": "Max",
            "nachname": "Mustermann",
            "emailadressen": [
                {"adresse": "max.mustermann@example.com"}
            ],
        },
    }
    usage = {"cpu_hours": 1.0, "gpu_hours": 0.5, "ram_gb_hours": 2.0}

    with mock.patch("usage_report.report.SimAPI") as MockAPI:
        api_instance = MockAPI.return_value
        api_instance.fetch_user.return_value = user_info
        with mock.patch("usage_report.report.fetch_usage", return_value=usage):
            with mock.patch("usage_report.report.list_user_groups", return_value=["users", "project-ai-c", "other"]):
                report = create_report("mm123", "2025-01-01")
    assert report["email"] == "max.mustermann@example.com"
    csv_path = write_report_csv(
        report,
        tmp_path,
        "out.csv",
        start="2025-01-01",
        partitions=["gpu"],
    )
    assert csv_path.exists()
    content = csv_path.read_text()
    assert "first_name,last_name" in content
    assert report["ai_c_group"] == "project-ai-c"


def test_create_report_multiple_ai_c(tmp_path):
    user_info = {
        "kennung": "mm123",
        "projekt": "proj",
        "daten": {
            "vorname": "Max",
            "nachname": "Mustermann",
            "emailadressen": [
                {"adresse": "max.mustermann@example.com"}
            ],
        },
    }
    usage = {"cpu_hours": 1.0, "gpu_hours": 0.5, "ram_gb_hours": 2.0}

    with mock.patch("usage_report.report.SimAPI") as MockAPI:
        api_instance = MockAPI.return_value
        api_instance.fetch_user.return_value = user_info
        with mock.patch("usage_report.report.fetch_usage", return_value=usage):
            with mock.patch(
                "usage_report.report.list_user_groups",
                return_value=["a-ai-c", "b-ai-c"],
            ):
                report = create_report("mm123", "2025-01-01")
    assert report["ai_c_group"] == "a-ai-c|b-ai-c"


def test_write_report_csv_append(tmp_path):
    row1 = {"first_name": "A", "last_name": "B"}
    csv_path = write_report_csv(row1, tmp_path, "out.csv", start="2025-01-01", partitions=["gpu"])
    row2 = {"first_name": "C", "last_name": "D"}
    csv_path = write_report_csv(row2, tmp_path, "out.csv", start="2025-02-01", partitions=["gpu"])
    lines = csv_path.read_text().splitlines()
    assert len(lines) == 3
    assert "timestamp" in lines[0]
    assert "partitions" in lines[0]


def test_create_active_reports():
    sample_active = {"partitions": ["gpu"], "user1": 5.0, "user2": 3.0}
    reports = [
        {"kennung": "user1", "cpu_hours": 1.0},
        {"kennung": "user2", "cpu_hours": 2.0},
    ]
    with mock.patch("usage_report.report.fetch_active_usage", return_value=sample_active) as fa:
        with mock.patch(
            "usage_report.report.create_report",
            side_effect=reports,
        ) as cr:
            rows = create_active_reports("2025-06-01", "2025-06-30", partitions=["gpu"])
    # ``fetch_active_usage`` no longer receives partition filters
    fa.assert_called_once_with("2025-06-01", "2025-06-30")
    assert cr.call_count == 2
    assert {call.args[0] for call in cr.call_args_list} == {"user1", "user2"}
    assert all("timestamp" in r for r in rows)
    assert all(r["period_start"] == "2025-06-01" for r in rows)


def test_enrich_report_rows():
    rows = [{"kennung": "user1", "cpu_hours": 1.0}]
    user_info = {
        "kennung": "user1",
        "projekt": "proj",
        "daten": {
            "vorname": "Max",
            "nachname": "Mustermann",
            "emailadressen": [{"adresse": "max@example.com"}],
        },
    }
    with mock.patch("usage_report.report.SimAPI") as MockAPI:
        api_inst = MockAPI.return_value
        api_inst.fetch_user.return_value = user_info
        with mock.patch(
            "usage_report.report.list_user_groups",
            return_value=["test-ai-c"],
        ):
            result = enrich_report_rows(rows)
    assert result[0]["first_name"] == "Max"
    assert result[0]["last_name"] == "Mustermann"
    assert result[0]["email"] == "max@example.com"
    assert result[0]["projekt"] == "proj"
    assert result[0]["ai_c_group"] == "test-ai-c"


def test_create_active_reports_skip_error():
    sample_active = {"partitions": [], "user1": 5.0, "bad": 3.0, "user2": 2.0}

    def fake_create(user, start, end, partitions=None, netrc_file=None):
        if user == "bad":
            raise SimAPIError("fail")
        return {"kennung": user}

    with mock.patch(
        "usage_report.report.fetch_active_usage", return_value=sample_active
    ) as fa:
        with mock.patch(
            "usage_report.report.create_report", side_effect=fake_create
        ) as cr:
            rows = create_active_reports("2025-06-01", "2025-06-30")

    # fetch_active_usage is called without partition filters
    fa.assert_called_once_with("2025-06-01", "2025-06-30")
    assert {call.args[0] for call in cr.call_args_list} == {"user1", "bad", "user2"}
    assert {r["kennung"] for r in rows} == {"user1", "user2"}
