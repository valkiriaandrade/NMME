"""Human-readable labels for map titles and colorbars."""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from pathlib import Path

SOURCE_CREDIT = "Data: NOAA NMME"

PRODUCT_NAMES: dict[str, str] = {
    "precipitation": "precipitation forecast",
    "precipitation-anomaly": "precipitation anomaly forecast",
    "temperature-anomaly": "temperature anomaly forecast",
}

#: NMME variable tokens found in provider file names (``NMME.tmax.202407...``).
VARIABLE_NAMES: dict[str, str] = {
    "tmax": "maximum temperature",
    "tmin": "minimum temperature",
    "tref": "2 m temperature",
    "sst": "sea surface temperature",
}

_UNIT_LABELS: dict[str, str] = {
    "k": "°C",  # used for anomalies only: a difference of 1 K equals 1 °C
    "degc": "°C",
    "mm/month": "mm/month",
}


def units_label(units: str | None) -> str:
    """Display label for anomaly/total units (``"K"`` -> ``"°C"``, ``"mm/month"`` unchanged)."""
    if not units:
        return ""
    return _UNIT_LABELS.get(units.strip().lower(), units.strip())


def model_label(files: Iterable[str | Path]) -> str:
    """Model name from provider file names: ``CFSv2.prate...`` -> ``"CFSv2"``.

    Several different models give ``"NMME N-model ensemble"``.
    """
    models = sorted({Path(f).name.split(".")[0] for f in files})
    if len(models) == 1:
        return models[0]
    return f"NMME {len(models)}-model ensemble"


def quantity_label(product: str, files: Iterable[str | Path]) -> str:
    """Quantity for the title, refining temperature anomalies by NMME variable token."""
    name = PRODUCT_NAMES.get(product, product)
    if product == "temperature-anomaly":
        tokens = {part.lower() for f in files for part in Path(f).name.split(".")}
        for token, variable in VARIABLE_NAMES.items():
            if token in tokens:
                return f"{variable} anomaly forecast"
    return name


def format_month(year: int, month: int) -> str:
    """``(2024, 5)`` -> ``"May 2024"``."""
    return f"{calendar.month_name[month]} {year}"


def format_title(
    model: str, quantity: str, period: str | None = None, region: str | None = None, units: str = ""
) -> str:
    """Build a map title with model, quantity, region, target month and units.

    >>> format_title("CFSv2", "precipitation forecast", "May 2024", "Brazil", "mm/month")
    'CFSv2 precipitation forecast – Brazil, May 2024 (mm/month)'
    """
    where = ", ".join(part for part in (region, period) if part)
    title = f"{model} {quantity}"
    if where:
        title += f" – {where}"
    if units:
        title += f" ({units})"
    return title
