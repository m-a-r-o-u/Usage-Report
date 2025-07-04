"""Usage Report library."""

from .api import SimAPI, SimAPIError
from .slurm import fetch_usage, parse_elapsed, parse_tres, parse_mem
from .report import (
    create_report,
    create_active_reports,
    write_report_csv,
    aggregate_rows,
)
from .sreport import fetch_active_usage, parse_sreport_output
from .database import store_month, load_month, list_months
from .groups import list_user_groups
from .plotting import create_donut_plot

__all__ = [
    "SimAPI",
    "SimAPIError",
    "fetch_usage",
    "parse_elapsed",
    "parse_tres",
    "parse_mem",
    "create_report",
    "create_active_reports",
    "write_report_csv",
    "aggregate_rows",
    "create_donut_plot",
    "list_user_groups",
    "fetch_active_usage",
    "parse_sreport_output",
    "store_month",
    "load_month",
    "list_months",
]
__version__ = "0.1.0"
