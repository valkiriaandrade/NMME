"""Download NMME forecast files from the public NOAA CPC server into ``data/``.

Source: NOAA Climate Prediction Center, North American Multi-Model Ensemble,
https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/<YYYYMM>0800/ (public domain).
Files are named ``<MODEL>.<variable>.<YYYYMM>.ENSMEAN.<anom|fcst>.nc``.

Usage::

    python scripts/download_data.py                   # everything `make figures` needs
    python scripts/download_data.py --run 202410 --variable prate --kind anom --model NMME
    python scripts/download_data.py --dry-run         # only list the URLs

Files that already exist are skipped (use ``--overwrite`` to fetch them again).
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

BASE_URL = "https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN"
ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "nmme-maps-data-download"
MODELS_202407 = [
    "CFSv2", "CanESM5", "GEM5.2_NEMO", "GFDL_SPEAR", "NASA_GEOS5v2", "NCAR_CCSM4", "NCAR_CESM1",
]  # fmt: skip

logger = logging.getLogger("download_data")


class DownloadError(RuntimeError):
    """A file could not be downloaded."""


@dataclass(frozen=True)
class Item:
    """One file to download: source URL and destination relative to the data folder."""

    url: str
    path: Path


def parse_run(value: str) -> str:
    """Validate a run month ``YYYYMM`` (argparse type)."""
    if not re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError(f"invalid run {value!r}; use YYYYMM, e.g. 202407")
    return value


def item(model: str, variable: str, run: str, kind: str, folder: str = "") -> Item:
    """One CPC ENSMEAN file, saved under ``folder`` in the data directory."""
    name = f"{model}.{variable}.{run}.ENSMEAN.{kind}.nc"
    return Item(f"{BASE_URL}/{run}0800/{name}", Path(folder) / name if folder else Path(name))


def figure_plan() -> list[Item]:
    """Every file used by ``make figures`` and the README examples."""
    return [
        item("CFSv2", "prate", "202404", "fcst"),
        item("NMME", "tmax", "202407", "anom"),
        item("NMME", "prate", "202407", "anom", "nmme_202407_anomalies"),
        *(item(m, "prate", "202407", "fcst", "nmme_202407_forecasts") for m in MODELS_202407),
    ]


def custom_plan(runs, variables, kind, models) -> list[Item]:
    """Files for other runs, saved under ``data/nmme_<run>_<anomalies|forecasts>/``."""
    folder = "anomalies" if kind == "anom" else "forecasts"
    return [
        item(model, variable, run, kind, f"nmme_{run}_{folder}")
        for run in runs
        for variable in variables
        for model in models
    ]


def fetch(
    url: str,
    dest: Path,
    *,
    overwrite: bool = False,
    retries: int = 3,
    timeout: float = 120,
    opener: Callable = urllib.request.urlopen,
) -> bool:
    """Download ``url`` to ``dest``; return False if it was skipped because it exists.

    The file is written to ``<dest>.part`` first and renamed when complete.

    Raises:
        DownloadError: if the file does not exist on the server or every attempt fails.
    """
    if dest.exists() and dest.stat().st_size > 0 and not overwrite:
        logger.debug("Already present: %s", dest)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener(request, timeout=timeout) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
            partial.replace(dest)
            return True
        except urllib.error.HTTPError as error:
            partial.unlink(missing_ok=True)
            if error.code == 404:
                raise DownloadError(
                    f"Not found on the server: {url} (check the run month, variable and model)"
                ) from error
            last_error = error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            partial.unlink(missing_ok=True)
            last_error = error
        if attempt < retries:
            time.sleep(2 * attempt)
    raise DownloadError(f"Could not download {url} after {retries} attempts: {last_error}")


def download(items: Iterable[Item], data_dir: Path, *, overwrite: bool = False) -> list[str]:
    """Download every item; return the error messages of the ones that failed."""
    errors, fetched, skipped = [], 0, 0
    for item in items:
        try:
            if fetch(item.url, data_dir / item.path, overwrite=overwrite):
                fetched += 1
                logger.info("Downloaded %s", item.path)
            else:
                skipped += 1
        except DownloadError as error:
            errors.append(str(error))
            logger.error("%s", error)
    logger.info("%d downloaded, %d already present, %d failed", fetched, skipped, len(errors))
    return errors


def build_parser() -> argparse.ArgumentParser:
    """Command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run", nargs="+", type=parse_run, metavar="YYYYMM", help="initialisation month(s)"
    )
    parser.add_argument("--variable", nargs="+", default=["prate"], help="e.g. prate tmax tmin")
    parser.add_argument("--kind", choices=["anom", "fcst"], default="anom")
    parser.add_argument("--model", nargs="+", default=["NMME"], help="NMME or single models")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--overwrite", action="store_true", help="download existing files again")
    parser.add_argument("--dry-run", action="store_true", help="only list the URLs")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit status."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.run:
        items = custom_plan(args.run, args.variable, args.kind, args.model)
    else:
        items = figure_plan()
    if args.dry_run:
        for entry in items:
            print(f"{entry.url} -> {args.data_dir / entry.path}")
        return 0
    errors = download(items, args.data_dir, overwrite=args.overwrite)
    if errors:
        logger.error("%d file(s) could not be downloaded:\n  %s", len(errors), "\n  ".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
