# Usage Report

Utilities to fetch information from the LRZ SIM API and to calculate Slurm usage statistics.

## Installation

```bash
pip install -e .
```

## Command line usage

```bash
# fetch information from the SIM API
usage sim <user_id> [--netrc-file PATH]

# aggregate Slurm usage
usage slurm <user_id> -S 2025-06-27 [-E 2025-06-30]
# or entire month
usage slurm <user_id> --month 2025-06
# filter by partition (can be used multiple times, supports wildcards)
usage slurm <user_id> --month 2025-06 \
    --partition lrz* --partition mcml*
# quote wildcards to prevent shell expansion if needed
# usage slurm <user_id> --month 2025-06 \
#     --partition 'lrz*' --partition 'mcml*'

# cluster usage for active users
usage report active -S 2025-06-27 [-E 2025-06-30] [--netrc-file PATH]

# combined report
usage report <user_id> -S 2025-06-27 [-E 2025-06-30] [--netrc-file PATH]
# or for a whole month
usage report <user_id> --month 2025-06 [--netrc-file PATH]
    --partition lrz* --partition mcml*
# list stored monthly data
usage report list
# show stored month
usage report show --month 2025-06 [--netrc-file PATH]
```
