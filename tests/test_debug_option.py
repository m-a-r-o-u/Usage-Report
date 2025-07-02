import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from usage_report.cli import parse_args


def test_parse_debug():
    args = parse_args(["--debug", "report", "list"])
    assert args.debug is True


def test_parse_debug_end():
    args = parse_args(["report", "active", "--month", "2025-06", "--debug"])
    assert args.debug is True
