"""Plotting utilities for Usage Report."""
from __future__ import annotations

from typing import Iterable
import sys


def create_donut_plot(
    rows: Iterable[dict[str, object]],
    column: str,
    *,
    start: str | None = None,
    end: str | None = None,
    title: str | None = None,
) -> None:
    """Create a donut plot from *rows* using *column* values.

    The plot is saved as ``usage_plot.png`` in the current directory.  If
    matplotlib is not available, a message is printed and the function returns
    without raising an exception.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # always use a non-interactive backend
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"Plotting requires matplotlib: {exc}", file=sys.stderr)
        return

    data: list[tuple[str, float]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        val = float(row.get(column, 0) or 0)
        label = str(row.get("ai_c_group") or row.get("kennung") or "")
        data.append((label, val))

    if not data:
        print("No data to plot", file=sys.stderr)
        return

    data.sort(key=lambda t: t[1])
    max_val = data[-1][1]
    threshold = max_val * 1.05
    other_total = 0.0
    labels: list[str] = []
    values: list[float] = []

    for label, val in data:
        if other_total <= threshold - val:
            other_total += val
        else:
            labels.append(label)
            values.append(val)

    if other_total > 0:
        labels.append("Others")
        values.append(other_total)

    colors = matplotlib.cm.tab20.colors
    plt.figure(figsize=(10, 10))
    wedges, texts, autotexts = plt.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.85,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
        colors=colors,
    )
    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    plt.gca().add_artist(centre_circle)
    for text in texts:
        text.set(size=10)
    for autotext in autotexts:
        autotext.set(size=9, weight="bold")
    if title is None:
        period = f"{start or '?'} - {end or '?'}" if start or end else None
        title = f"{column.replace('_', ' ').title()} by Group"
        if period:
            title += f" ({period})"
    plt.title(title, fontsize=14, pad=40)
    plt.axis("equal")
    plt.savefig("usage_plot.png")
    plt.close()
    print("Plot saved to usage_plot.png")

__all__ = ["create_donut_plot"]
