"""Formatting helpers for human-readable output."""

from __future__ import annotations

import math


def format_quantity(value: float, precision: int = 3) -> str:
    """Format quantities without float noise and without decimals for integers."""
    if value is None:
        return ""
    if math.isclose(value, round(value), rel_tol=0.0, abs_tol=1e-9):
        return str(int(round(value)))

    rounded = round(float(value), precision)
    text = f"{rounded:.{precision}f}".rstrip("0").rstrip(".")
    return text
