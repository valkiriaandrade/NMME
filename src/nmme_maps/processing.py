"""Forecast-month bookkeeping, unit conversion and ensemble mean."""

from __future__ import annotations

import calendar
from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr

from .io import align_exact, read_field

SECONDS_PER_DAY = 86400


def month_sequence(start: str, count: int) -> Iterator[tuple[int, int]]:
    """Yield ``(year, month)`` for ``count`` consecutive months from ``start`` (``YYYY-MM``)."""
    try:
        date = datetime.strptime(start, "%Y-%m")
    except ValueError as error:
        raise ValueError(f"Invalid month {start!r}; use the YYYY-MM format") from error
    for offset in range(count):
        year, month = divmod(date.year * 12 + date.month - 1 + offset, 12)
        yield year, month + 1


def monthly_total(rate: np.ndarray | float, year: int, month: int, units: str):
    """Convert a precipitation rate to a monthly total in mm, with the Gregorian calendar.

    Args:
        rate: precipitation rate in ``units``.
        year, month: target month (sets 28/29/30/31 days).
        units: ``"mm/s"``, ``"mm/day"`` or ``"mm/month"``.

    Raises:
        ValueError: for any other unit.
    """
    days = calendar.monthrange(year, month)[1]
    if units == "mm/s":
        return rate * days * SECONDS_PER_DAY
    if units == "mm/day":
        return rate * days
    if units == "mm/month":
        return rate
    raise ValueError(f"Unsupported precipitation unit {units!r}; use mm/s, mm/day or mm/month")


def ensemble(files: Sequence[str | Path], variable: str = "fcst") -> xr.DataArray:
    """Equal-weight mean of the members in ``files``; missing values propagate.

    Raises:
        ValueError: if no files are given or grids differ.
    """
    if not files:
        raise ValueError("No ensemble members given; pass one or more NetCDF files to --input")
    fields = [read_field(path, variable) for path in files]
    return xr.concat(align_exact(*fields), dim="member").mean("member", skipna=False)
