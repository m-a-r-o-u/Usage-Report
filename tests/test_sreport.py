from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from unittest import mock

from usage_report.sreport import fetch_active_usage, parse_sreport_output


def test_parse_sreport_output():
    text = """
 Login  Used
 user1  10
 user2  5
    """
    result = parse_sreport_output(text)
    assert result == {"user1": 10.0, "user2": 5.0}


def test_fetch_active_usage():
    sample_output = """
 Login  Used
 user1  10
 user2  5
    """
    mocked_proc = mock.Mock(stdout=sample_output)
    with mock.patch("subprocess.run", return_value=mocked_proc):
        usage = fetch_active_usage("2025-06-01", "2025-06-30", active_users=["user1", "user2"])
    assert usage == {"user1": 10.0, "user2": 5.0}
