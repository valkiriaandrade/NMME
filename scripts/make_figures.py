"""Regenerate every figure in ``figures/`` from the data in ``data/``.

Usage::

    python scripts/make_figures.py [--data-dir data] [--figures-dir figures] [--dpi 200]

Figures whose source data is not in the repository are skipped with a warning and
the existing images are kept. A figure set that fails does not stop the others. The exit
status is 1 if any figure set was skipped or failed.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from nmme_maps.cli import main as nmme_maps

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger("make_figures")

TMAX_MONTHS = [f"2024-{m:02d}" for m in range(7, 13)] + [f"2025-{m:02d}" for m in range(1, 4)]


@dataclass(frozen=True)
class FigureSet:
    """A group of published figures produced by one ``nmme-maps`` call."""

    name: str
    inputs: list[str]
    options: list[str]
    subdir: str = ""
    months: list[str] = field(default_factory=list)


FIGURE_SETS = [
    FigureSet(
        "CFSv2 precipitation, May 2024 (run of April 2024)",
        ["CFSv2.prate.202404.ENSMEAN.fcst.nc"],
        [
            "--product", "precipitation", "--start", "2024-04", "--units", "mm/s",
            "--filename", "cfsv2_precipitation_{year}-{month:02d}.png",
        ],
        months=["2024-05"],
    ),
    FigureSet(
        "NMME maximum temperature anomaly, Jul 2024 - Mar 2025",
        ["NMME.tmax.202407.ENSMEAN.anom.nc"],
        [
            "--product", "temperature-anomaly", "--start", "2024-07",
            "--filename", "nmme_tmax_anomaly_{year}-{month:02d}.png",
        ],
        months=TMAX_MONTHS,
    ),
    # NMME ensemble precipitation ANOMALY of the July 2024 run (NOAA CPC); not committed,
    # fetched by `make data` into data/nmme_202407_anomalies/.
    FigureSet(
        "NMME precipitation anomaly, Jul 2024 - Mar 2025",
        ["nmme_202407_anomalies"],
        [
            "--product", "precipitation-anomaly", "--start", "2024-07", "--units", "mm/s",
            "--filename", "nmme_precipitation_anomaly_{year}-{month:02d}.png",
        ],
        subdir="precipitation_anomaly",
        months=TMAX_MONTHS,
    ),
]  # fmt: skip


def resolve_inputs(data_dir: Path, inputs: list[str]) -> list[Path]:
    """Expand directories to the NetCDF files they contain."""
    paths = []
    for item in inputs:
        path = data_dir / item
        paths += sorted(path.glob("*.nc")) if path.is_dir() else [path]
    return paths


#: IBGE state boundaries drawn on every map (downloaded by `make data`).
STATE_BORDERS = Path("BR_UF_2022") / "BR_UF_2022.zip"


def build(data_dir: Path, figures_dir: Path, dpi: int) -> tuple[list[str], list[str]]:
    """Rebuild every figure set with available data; return the names skipped and failed."""
    skipped, failed = [], []
    borders = data_dir / STATE_BORDERS
    for figure_set in FIGURE_SETS:
        inputs = resolve_inputs(data_dir, figure_set.inputs)
        missing = [str(p) for p in inputs if not p.exists()] or ([] if inputs else ["inputs"])
        if not borders.exists():
            missing.append(str(borders))
        if missing:
            logger.warning(
                "Skipping %s (kept existing images): missing %s; run `make data`",
                figure_set.name,
                ", ".join(missing),
            )
            skipped.append(figure_set.name)
            continue
        logger.info("Building %s", figure_set.name)
        args = ["--input", *map(str, inputs), *figure_set.options]
        if figure_set.months:
            args += ["--months", *figure_set.months]
        args += ["--borders", str(borders)]
        args += ["--dpi", str(dpi), "--output", str(figures_dir / figure_set.subdir)]
        try:
            nmme_maps(args)
        except SystemExit as error:  # the CLI reports expected errors with exit status 2
            if error.code:
                logger.error("Failed: %s", figure_set.name)
                failed.append(figure_set.name)
        except Exception:
            logger.exception("Failed: %s", figure_set.name)
            failed.append(figure_set.name)
    return skipped, failed


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--figures-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    skipped, failed = build(args.data_dir, args.figures_dir, args.dpi)
    built = len(FIGURE_SETS) - len(skipped) - len(failed)
    logger.info(
        "Done: %d figure set(s) regenerated, %d skipped, %d failed",
        built,
        len(skipped),
        len(failed),
    )
    return 1 if skipped or failed else 0


if __name__ == "__main__":
    sys.exit(main())
