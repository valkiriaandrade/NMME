import argparse

import numpy as np
import pytest
import xarray as xr

from nmme_maps.arguments import positive_int
from nmme_maps.cli import build_cli, main, output_name
from nmme_maps.labels import (
    format_month,
    format_title,
    model_label,
    quantity_label,
    units_label,
)
from nmme_maps.processing import SECONDS_PER_DAY, month_sequence, monthly_total
from nmme_maps.regions import normalize_region

BASE = ["--input", "a.nc", "--start", "2024-07", "--output", "out"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("brazil", "brazil"),
        ("north", "north"),
        ("south", "south"),
        ("brasil", "brazil"),
        ("norte", "north"),
        ("sul", "south"),
        ("Sul", "south"),
    ],
)
def test_region_names_and_portuguese_aliases(value, expected):
    assert normalize_region(value) == expected


def test_unknown_region():
    with pytest.raises(argparse.ArgumentTypeError, match="choose one of"):
        normalize_region("east")


def test_cli_region_alias_dpi_and_months():
    args = build_cli().parse_args([*BASE, "--region", "norte", "--months", "2024-08", "2024-09"])
    assert args.region == "north"
    assert args.dpi == 200
    assert args.months == ["2024-08", "2024-09"]
    assert build_cli().parse_args([*BASE, "--dpi", "120"]).dpi == 120
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("abc")


def test_unit_conversion_rate_to_monthly_total():
    rate = np.array([1e-5, 2e-5])  # mm/s
    np.testing.assert_allclose(monthly_total(rate, 2024, 5, "mm/s"), rate * 31 * SECONDS_PER_DAY)
    np.testing.assert_allclose(monthly_total(3.0, 2024, 2, "mm/day"), 87.0)  # leap year
    assert units_label("K") == "°C"  # anomaly: 1 K difference = 1 °C
    assert units_label("mm/month") == "mm/month"
    assert units_label(None) == ""


def test_invalid_start_month():
    with pytest.raises(ValueError, match="YYYY-MM"):
        list(month_sequence("07/2024", 2))


def test_title_and_labels():
    files = ["data/NMME.tmax.202407.ENSMEAN.anom.nc"]
    assert model_label(files) == "NMME"
    assert model_label(["CFSv2.prate.x.nc", "CanESM5.prate.x.nc"]) == "NMME 2-model ensemble"
    assert quantity_label("temperature-anomaly", files) == "maximum temperature anomaly forecast"
    assert quantity_label("precipitation", ["CFSv2.prate.nc"]) == "precipitation forecast"
    assert format_month(2025, 1) == "January 2025"
    assert (
        format_title("NMME", "maximum temperature anomaly forecast", "October 2024", "Brazil", "°C")
        == "NMME maximum temperature anomaly forecast – Brazil, October 2024 (°C)"
    )


def test_output_name_template():
    assert output_name("{product}_{year}-{month:02d}.png", "precipitation", 2025, 3) == (
        "precipitation_2025-03.png"
    )
    with pytest.raises(ValueError, match="template"):
        output_name("{unknown}.png", "precipitation", 2025, 3)


def test_months_filter_and_missing_units(tmp_path, monkeypatch):
    path = tmp_path / "CFSv2.prate.202404.ENSMEAN.fcst.nc"
    xr.Dataset(
        {"fcst": (("target", "lat", "lon"), np.ones((3, 2, 2)))},
        coords={"target": [0, 1, 2], "lat": [-10.0, -9.0], "lon": [300.0, 301.0]},
    ).to_netcdf(path, engine="h5netcdf")
    calls = []
    monkeypatch.setattr("nmme_maps.cli.plot_map", lambda *a, **k: calls.append(k["title"]))
    main(["--input", str(path), "--start", "2024-04", "--units", "mm/s", "--output",
          str(tmp_path), "--months", "2024-05"])  # fmt: skip
    assert calls == ["CFSv2 precipitation forecast – Brazil, May 2024 (mm/month)"]
    with pytest.raises(SystemExit):
        main(["--input", str(path), "--start", "2024-04", "--output", str(tmp_path)])
