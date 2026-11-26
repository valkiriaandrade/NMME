"""``nmme-maps`` command: one map per forecast target month."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from .arguments import build_parser, execute
from .colour_scales import colour_scale
from .io import spatial
from .labels import (
    SOURCE_CREDIT,
    format_month,
    format_title,
    model_label,
    quantity_label,
    units_label,
)
from .plotting import plot_map
from .processing import ensemble, month_sequence, monthly_total, rate_units, target_months
from .regions import ALIASES, REGIONS, normalize_region

logger = logging.getLogger(__name__)

PRODUCTS = ["precipitation", "precipitation-anomaly", "temperature-anomaly"]
DEFAULT_FILENAME = "{product}_{year}-{month:02d}.png"


def output_name(template: str, product: str, year: int, month: int) -> str:
    """Fill the ``--filename`` template for one target month.

    >>> output_name("nmme_{year}-{month:02d}.png", "precipitation", 2024, 7)
    'nmme_2024-07.png'
    """
    try:
        return template.format(product=product, year=year, month=month)
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"Invalid --filename template {template!r}; available fields: "
            "{product}, {year}, {month}"
        ) from error


def expand_inputs(inputs: Sequence[str]) -> list[Path]:
    """``--input`` entries, with each folder replaced by the ``*.nc`` files it contains."""
    paths: list[Path] = []
    for entry in map(Path, inputs):
        if entry.is_dir():
            found = sorted(entry.glob("*.nc"))
            if not found:
                raise ValueError(f"No .nc files in {entry}")
            paths += found
        else:
            paths.append(entry)
    return paths


def forecast_months(field, target_dim: str, start: str | None) -> list[tuple[int, int]]:
    """Target month of each forecast step, from the file's target axis when it has one.

    ``start`` (``YYYY-MM``) is required for files without a ``months since`` axis and,
    when given for a file that has one, must match its first target month.
    """
    count = field.sizes[target_dim]
    months = target_months(field[target_dim]) if target_dim in field.coords else None
    if months is None:
        if start is None:
            raise ValueError(
                f"The {target_dim!r} axis does not give calendar months; pass --start YYYY-MM "
                "(the first target month)"
            )
        return list(month_sequence(start, count))
    first = f"{months[0][0]}-{months[0][1]:02d}"
    if start is not None and start != first:
        raise ValueError(
            f"--start {start} does not match the file, whose first target month is {first} "
            "(in NOAA CPC files, the initialisation month); omit --start to use the file"
        )
    return months


def precipitation_units(field, requested: str | None) -> str:
    """Rate unit of a precipitation field: the file's ``units``, checked against ``--units``."""
    declared = field.attrs.get("units")
    found = rate_units(declared)
    if requested is None:
        if found is None:
            raise ValueError(
                f"Precipitation units {declared!r} not recognised; pass --units mm/s, "
                "mm/day or mm/month"
            )
        return found
    if declared is not None and found != requested:
        raise ValueError(f"--units {requested} contradicts the file, which declares {declared!r}")
    return requested


def selected_months(
    months: list[tuple[int, int]], wanted: Sequence[str] | None
) -> list[tuple[int, int]]:
    """The target months listed in ``--months`` (all of them by default).

    Raises:
        ValueError: if an entry is not ``YYYY-MM`` or not a target month of the file.
    """
    if not wanted:
        return months
    available = {f"{y}-{m:02d}": (y, m) for y, m in months}
    unknown = [w for w in wanted if w not in available]
    if unknown:
        first, last = months[0], months[-1]
        raise ValueError(
            f"--months {' '.join(unknown)} not in the forecast "
            f"({first[0]}-{first[1]:02d} to {last[0]}-{last[1]:02d}); use YYYY-MM"
        )
    return [ym for key, ym in available.items() if key in set(wanted)]


def run(args: argparse.Namespace) -> None:
    """Average the members and draw one map per selected target month."""
    field = ensemble(expand_inputs(args.input), args.variable)
    if args.target_dim not in field.dims:
        raise ValueError(
            f"Forecast dimension {args.target_dim!r} not found (dimensions: "
            f"{', '.join(map(str, field.dims))}); set --target-dim"
        )
    temperature = args.product == "temperature-anomaly"
    anomaly = args.product != "precipitation"
    rate = None if temperature else precipitation_units(field, args.units)
    scale = colour_scale(args.product)
    units = units_label("K") if temperature else "mm/month"
    if temperature:
        label = f"Temperature anomaly ({units})"
    elif anomaly:
        label = f"Precipitation anomaly ({units})"
    else:
        label = f"Precipitation ({units})"
    model = model_label(args.input)
    quantity = quantity_label(args.product, args.input)
    region = REGIONS[args.region]
    months = forecast_months(field, args.target_dim, args.start)
    for year, month in selected_months(months, args.months):
        index = months.index((year, month))
        selected = spatial(field.isel({args.target_dim: index}, drop=True))
        values = selected.values
        if not temperature:
            values = monthly_total(values, year, month, rate)
        output = Path(args.output) / output_name(args.filename, args.product, year, month)
        when = format_month(year, month)
        if args.title:
            title = args.title.replace("{month}", when)
        else:
            title = format_title(model, quantity, when, region.label, units)
        plot_map(
            values,
            selected.lat,
            selected.lon,
            output,
            title=title,
            label=label,
            levels=scale.levels,
            cmap=scale.cmap,
            extend=scale.extend,
            shapefile=args.shapefile,
            states=list(region.states) if region.states and args.shapefile else None,
            extent=list(region.extent),
            credit=SOURCE_CREDIT,
            dpi=args.dpi,
        )
        logger.info("Wrote %s", output)


def build_cli() -> argparse.ArgumentParser:
    """Return the parser for the ``nmme-maps`` command."""
    parser = build_parser(
        "NMME monthly forecast maps, one per target month. Anomaly products must be "
        "given anomaly files; no climatology is subtracted."
    )
    for action in parser._actions:
        if action.dest == "output":
            action.help = "output directory (one PNG per target month)"
        if action.dest == "title":
            action.help = "custom map title; {month} is replaced by each target month"
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="one or more NetCDF ensemble members, or folders of them (all *.nc inside)",
    )
    parser.add_argument(
        "--start",
        help="first target month, YYYY-MM. Read from the file's target axis when it has one "
        "(in NOAA CPC files it is the initialisation month); if given, it must match. "
        "Required for files without a 'months since' target axis",
    )
    parser.add_argument("--variable", default="fcst", help="NetCDF variable to read")
    parser.add_argument("--target-dim", default="target", help="forecast-month dimension")
    parser.add_argument(
        "--units",
        choices=["mm/s", "mm/day", "mm/month"],
        help="precipitation rate unit in the file (default: its units attribute; if given, "
        "it must agree with it)",
    )
    parser.add_argument("--product", choices=PRODUCTS, default="precipitation")
    parser.add_argument(
        "--region",
        type=normalize_region,
        choices=list(REGIONS),
        default="brazil",
        help=f"map domain (Portuguese aliases accepted: {', '.join(ALIASES)})",
    )
    parser.add_argument(
        "--months",
        nargs="+",
        metavar="YYYY-MM",
        help="only plot these target months (default: every month in the file)",
    )
    parser.add_argument(
        "--filename",
        default=DEFAULT_FILENAME,
        help="output file name template; fields: {product}, {year}, {month}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point of the ``nmme-maps`` command."""
    execute(build_cli(), run, argv)
