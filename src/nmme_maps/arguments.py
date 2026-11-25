"""Command-line options shared by every entry point."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence

from .plotting import DEFAULT_DPI

logger = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    """Argparse type for strictly positive integers (used by ``--dpi``)."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from error
    if number <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {number}")
    return number


def build_parser(description: str) -> argparse.ArgumentParser:
    """Create a parser with the options common to all maps."""
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--output", required=True, help="output PNG file")
    parser.add_argument("--title", help="custom map title (default: built from the data)")
    parser.add_argument(
        "--shapefile",
        help="state boundaries (.shp, or a zipped shapefile) with a defined CRS; "
        "used for masking and borders",
    )
    parser.add_argument(
        "--dpi", type=positive_int, default=DEFAULT_DPI, help="resolution of the PNG file"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="debug logging and full tracebacks on errors"
    )
    return parser


def execute(
    parser: argparse.ArgumentParser,
    operation: Callable[[argparse.Namespace], None],
    argv: Sequence[str] | None = None,
) -> None:
    """Parse ``argv``, configure logging and run ``operation``.

    Expected errors (bad input, missing files, missing optional dependencies) are
    reported as a one-line message with exit status 2; ``--verbose`` re-raises them.
    """
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        operation(args)
    except (ValueError, OSError, KeyError, ImportError) as error:
        if args.verbose:
            raise
        parser.exit(2, f"Error: {error}\n")
    logger.info("Output written to %s", args.output)
