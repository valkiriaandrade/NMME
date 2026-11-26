"""Forecast-month bookkeeping, unit conversion and ensemble mean."""

from __future__ import annotations

import calendar
import re
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


def target_months(coordinate: xr.DataArray) -> list[tuple[int, int]] | None:
    """``(year, month)`` of each forecast target from a ``months since YYYY-MM…`` axis.

    NOAA CPC NMME files store the target axis this way; their first target is the
    initialisation month (``target = 774`` is July 2024 in the July 2024 run). Returns
    ``None`` if the axis has other units or non-finite values.

    >>> axis = xr.DataArray([774.0, 775.0], attrs={"units": "months since 1960-01-01 12:00:00"})
    >>> target_months(axis)
    [(2024, 7), (2024, 8)]
    """
    match = re.match(r"\s*months since (\d{4})-(\d{1,2})", str(coordinate.attrs.get("units", "")))
    values = np.asarray(coordinate.values, dtype=float)
    if not match or values.ndim != 1 or not np.isfinite(values).all():
        return None
    base = int(match[1]) * 12 + int(match[2]) - 1
    months = []
    for value in values:
        year, month = divmod(base + int(np.floor(value + 1e-6)), 12)
        months.append((year, month + 1))
    return months


#: Spellings of the precipitation rate units in NetCDF files.
RATE_UNITS = {
    "mm/s": {"mm/s", "mm s-1", "mm s**-1", "kg m-2 s-1", "kg/m2/s", "kg m**-2 s**-1"},
    "mm/day": {"mm/day", "mm/d", "mm d-1", "mm day-1"},
    "mm/month": {"mm/month", "mm month-1"},
}


def rate_units(declared: object) -> str | None:
    """``mm/s``, ``mm/day`` or ``mm/month`` for a ``units`` attribute; ``None`` if unknown.

    >>> rate_units("mm/s"), rate_units("kg m-2 s-1"), rate_units("K")
    ('mm/s', 'mm/s', None)
    """
    text = " ".join(str(declared).split()).lower() if declared is not None else ""
    return next((unit for unit, names in RATE_UNITS.items() if text in names), None)


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
    units = {str(field.attrs.get("units")) for field in fields}
    if len(units) > 1:
        raise ValueError(f"Ensemble members have different units: {', '.join(sorted(units))}")
    # keep_attrs: the units of the members stay on the mean
    return xr.concat(align_exact(*fields), dim="member").mean(
        "member", skipna=False, keep_attrs=True
    )
