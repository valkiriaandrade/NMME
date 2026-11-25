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
from .processing import ensemble, month_sequence, monthly_total
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


def run(args: argparse.Namespace) -> None:
    """Average the members and draw one map per selected target month."""
    field = ensemble(args.input, args.variable)
    if args.target_dim not in field.dims:
        raise ValueError(
            f"Forecast dimension {args.target_dim!r} not found (dimensions: "
            f"{', '.join(map(str, field.dims))}); set --target-dim"
        )
    temperature = args.product == "temperature-anomaly"
    anomaly = args.product != "precipitation"
    if not temperature and args.units is None:
        raise ValueError(
            "Precipitation needs an explicit rate unit; pass --units mm/s, mm/day or mm/month"
        )
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
    months = list(month_sequence(args.start, field.sizes[args.target_dim]))
    wanted = set(args.months) if args.months else None
    if wanted and not wanted & {f"{y}-{m:02d}" for y, m in months}:
        first, last = months[0], months[-1]
        raise ValueError(
            f"None of --months {sorted(wanted)} is in the forecast "
            f"({first[0]}-{first[1]:02d} to {last[0]}-{last[1]:02d})"
        )
    for index, (year, month) in enumerate(months):
        if wanted and f"{year}-{month:02d}" not in wanted:
            continue
        selected = spatial(field.isel({args.target_dim: index}, drop=True))
        values = selected.values
        if not temperature:
            values = monthly_total(values, year, month, args.units)
        output = Path(args.output) / output_name(args.filename, args.product, year, month)
        title = args.title or format_title(
            model, quantity, format_month(year, month), region.label, units
        )
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
    parser.add_argument(
        "--input", nargs="+", required=True, help="one or more NetCDF ensemble members"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="first TARGET month of the file, YYYY-MM (not the initialisation month)",
    )
    parser.add_argument("--variable", default="fcst", help="NetCDF variable to read")
    parser.add_argument("--target-dim", default="target", help="forecast-month dimension")
    parser.add_argument(
        "--units",
        choices=["mm/s", "mm/day", "mm/month"],
        help="precipitation rate unit in the file (required for precipitation products)",
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
