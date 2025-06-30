from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from unittest import mock

from usage_report.report import create_report, _pick_email, write_report_csv


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
    csv_path = write_report_csv(report, tmp_path, "out.csv", start="2025-01-01")
    assert csv_path.exists()
    content = csv_path.read_text()
    assert "first_name,last_name" in content
    assert report["ai_c_group"] == "project-ai-c"


def test_write_report_csv_append(tmp_path):
    row1 = {"first_name": "A", "last_name": "B"}
    csv_path = write_report_csv(row1, tmp_path, "out.csv", start="2025-01-01")
    row2 = {"first_name": "C", "last_name": "D"}
    csv_path = write_report_csv(row2, tmp_path, "out.csv", start="2025-02-01")
    lines = csv_path.read_text().splitlines()
    assert len(lines) == 3
    assert "timestamp" in lines[0]
