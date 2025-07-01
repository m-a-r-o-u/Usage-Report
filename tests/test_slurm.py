from __future__ import annotations

from unittest import mock

import pytest

from usage_report.slurm import parse_elapsed, parse_mem, fetch_usage


def test_parse_elapsed():
    assert parse_elapsed("01:00:00") == 1
    assert parse_elapsed("1-00:00:00") == 24
    assert parse_elapsed("2-02:30:00") == 2 * 24 + 2.5


def test_parse_mem():
    assert parse_mem("1024M") == pytest.approx(1)
    assert parse_mem("1G") == 1
    assert parse_mem("1T") == 1024


def test_fetch_usage():
    sample = (
        "JobID|Partition|Elapsed|NCPUS|AllocTRES\n"
        "123|gpu|01:00:00|4|cpu=4,mem=8000M,gres/gpu=2\n"
        "123.batch|gpu|00:10:00|4|cpu=4,mem=8000M,gres/gpu=2\n"
    )
    mocked_proc = mock.Mock(stdout=sample)
    with mock.patch("subprocess.run", return_value=mocked_proc):
        usage = fetch_usage("user", "2025-01-01")
    assert usage["cpu_hours"] == 4.0
    assert usage["gpu_hours"] == 2.0
    assert usage["ram_gb_hours"] == pytest.approx(8.0, rel=0.05)


def test_fetch_usage_partition_filter():
    sample = (
        "JobID|Partition|Elapsed|NCPUS|AllocTRES\n"
        "1|lrz-gpu|01:00:00|4|cpu=4,mem=8000M,gres/gpu=2\n"
        "2|mcml-cpu|02:00:00|8|cpu=8,mem=16000M\n"
    )
    mocked_proc = mock.Mock(stdout=sample)
    with mock.patch("subprocess.run", return_value=mocked_proc):
        usage = fetch_usage("user", "2025-01-01", partitions=["lrz*"])
    assert usage["gpu_hours"] == 2.0
    assert usage["cpu_hours"] == 4.0

