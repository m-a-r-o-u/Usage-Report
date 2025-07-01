# Usage Report

Utilities to fetch information from the LRZ SIM API and to calculate Slurm usage statistics.

## Installation

```bash
pip install -e .
```

## Command line usage

```bash
# fetch information from the SIM API
usage-report api <user_id> [--netrc-file PATH]

# aggregate Slurm usage
usage-report slurm <user_id> -S 2025-06-27 [-E 2025-06-30]
# or entire month
usage-report slurm <user_id> --month 2025-06

# combined report
usage-report report <user_id> -S 2025-06-27 [-E 2025-06-30] [--netrc-file PATH]
# or for a whole month
usage-report report <user_id> --month 2025-06 [--netrc-file PATH]
```
