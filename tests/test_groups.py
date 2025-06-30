from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from unittest import mock

from usage_report.groups import list_user_groups


def test_list_user_groups():
    sample_output = "uid=1000(user) gid=1000(user) groups=1000(user),27(sudo),111(test-ai-c)\n"
    mocked_proc = mock.Mock(stdout=sample_output)
    with mock.patch("subprocess.run", return_value=mocked_proc):
        groups = list_user_groups("user")
    assert groups == ["user", "sudo", "test-ai-c"]
