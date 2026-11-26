"""Every product run end to end on netCDF3 files laid out like the NOAA CPC ones."""

import sys

import numpy as np
import pytest
import xarray as xr
from conftest import ROOT, load_script

from nmme_maps.cli import main

MONTHS_SINCE = "months since 1960-01-01 12:00:00"


def cpc_file(path, values, units, first_target=774.0):
    """A small CPC-style file (netCDF3, like every file on the CPC server)."""
    count = values.shape[0]
    xr.Dataset(
        {"fcst": (("target", "lat", "lon"), values, {"units": units})},
        coords={
            "target": ("target", first_target + np.arange(count), {"units": MONTHS_SINCE}),
            "lat": [-10.0, -9.0],
            "lon": [300.0, 301.0],
        },
    ).to_netcdf(path, engine="scipy")
    assert path.read_bytes()[:3] == b"CDF"
    return path


@pytest.fixture
def drawn(monkeypatch):
    """What the CLI passes to plot_map (nothing is drawn)."""
    calls = []
    monkeypatch.setattr(
        "nmme_maps.cli.plot_map",
        lambda values, lat, lon, output, **kw: calls.append(
            {"values": values, "output": output, **kw}
        ),
    )
    return calls


def test_precipitation_months_and_lengths_come_from_the_file(tmp_path, drawn):
    rate = np.full((3, 2, 2), 1e-5)  # mm/s
    path = cpc_file(tmp_path / "CFSv2.prate.202407.ENSMEAN.fcst.nc", rate, "mm/s")
    main(["--input", str(path), "--output", str(tmp_path / "out")])
    titles = [call["title"] for call in drawn]
    assert titles == [
        f"CFSv2 precipitation forecast – Brazil, {month} 2024 (mm/month)"
        for month in ("July", "August", "September")
    ]
    days = [31, 31, 30]
    for call, n in zip(drawn, days, strict=True):
        np.testing.assert_allclose(call["values"], 1e-5 * n * 86400)
    assert [call["output"].name for call in drawn] == [
        "precipitation_2024-07.png",
        "precipitation_2024-08.png",
        "precipitation_2024-09.png",
    ]
    assert drawn[0]["cmap"] == "jet" and drawn[0]["extend"] == "max"


def test_precipitation_anomaly_is_scaled_and_uses_brbg(tmp_path, drawn):
    path = cpc_file(
        tmp_path / "NMME.prate.202407.ENSMEAN.anom.nc", np.full((2, 2, 2), -2e-5), "mm/s"
    )
    main(["--product", "precipitation-anomaly", "--input", str(path), "--output", str(tmp_path)])
    np.testing.assert_allclose(drawn[1]["values"], -2e-5 * 31 * 86400)  # August
    assert drawn[0]["label"] == "Precipitation anomaly (mm/month)" and drawn[0]["cmap"] == "BrBG"
    assert drawn[0]["title"].startswith("NMME precipitation anomaly forecast – Brazil, July 2024")


def test_temperature_anomaly_is_never_scaled_by_month_length(tmp_path, drawn):
    path = cpc_file(tmp_path / "NMME.tmax.202407.ENSMEAN.anom.nc", np.full((2, 2, 2), 1.5), "K")
    main(["--product", "temperature-anomaly", "--input", str(path), "--output", str(tmp_path)])
    np.testing.assert_allclose(drawn[0]["values"], 1.5)
    assert drawn[0]["label"] == "Temperature anomaly (°C)"
    assert drawn[0]["title"] == (
        "NMME maximum temperature anomaly forecast – Brazil, July 2024 (°C)"
    )


def test_start_must_match_the_file(tmp_path, drawn, capsys):
    path = cpc_file(tmp_path / "NMME.prate.202407.ENSMEAN.anom.nc", np.ones((2, 2, 2)), "mm/s")
    main(["--input", str(path), "--start", "2024-07", "--output", str(tmp_path)])
    assert len(drawn) == 2
    with pytest.raises(SystemExit):  # the month after the initialisation month
        main(["--input", str(path), "--start", "2024-08", "--output", str(tmp_path)])
    assert "first target month is 2024-07" in capsys.readouterr().err


def test_start_is_required_without_a_months_since_axis(tmp_path, drawn, capsys):
    path = tmp_path / "plain.nc"
    xr.Dataset(
        {"fcst": (("target", "lat", "lon"), np.ones((2, 2, 2)), {"units": "mm/day"})},
        coords={"target": [0.5, 1.5], "lat": [-10.0, -9.0], "lon": [300.0, 301.0]},
    ).to_netcdf(path, engine="scipy")
    with pytest.raises(SystemExit):
        main(["--input", str(path), "--output", str(tmp_path)])
    assert "pass --start" in capsys.readouterr().err
    main(["--input", str(path), "--start", "2025-01", "--output", str(tmp_path)])
    np.testing.assert_allclose(drawn[1]["values"], 28)  # February 2025, mm/day
    assert drawn[1]["title"].endswith("February 2025 (mm/month)")


def test_units_must_agree_with_the_file(tmp_path, drawn, capsys):
    path = cpc_file(tmp_path / "NMME.prate.202407.ENSMEAN.anom.nc", np.ones((1, 2, 2)), "mm/s")
    with pytest.raises(SystemExit):
        main(["--input", str(path), "--units", "mm/day", "--output", str(tmp_path)])
    assert "contradicts the file" in capsys.readouterr().err
    unknown = cpc_file(tmp_path / "other.prate.nc", np.ones((1, 2, 2)), "furlongs")
    with pytest.raises(SystemExit):
        main(["--input", str(unknown), "--output", str(tmp_path)])
    main(["--input", str(unknown), "--units", "mm/month", "--output", str(tmp_path)])
    assert len(drawn) == 1


def test_months_must_all_be_in_the_forecast(tmp_path, drawn, capsys):
    path = cpc_file(tmp_path / "NMME.prate.202407.ENSMEAN.anom.nc", np.ones((3, 2, 2)), "mm/s")
    with pytest.raises(SystemExit):
        main(["--input", str(path), "--months", "2024-08", "2025-08", "--output", str(tmp_path)])
    assert "--months 2025-08 not in the forecast" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--input", str(path), "--months", "2024-8", "--output", str(tmp_path)])
    assert not drawn


def test_custom_title_with_month_and_folder_input(tmp_path, drawn):
    folder = tmp_path / "members"
    folder.mkdir()
    for model, value in [("CFSv2", 1e-5), ("CanESM5", 3e-5)]:
        cpc_file(
            folder / f"{model}.prate.202407.ENSMEAN.fcst.nc", np.full((2, 2, 2), value), "mm/s"
        )
    main(["--input", str(folder), "--title", "Ensemble, {month}", "--output", str(tmp_path)])
    assert [call["title"] for call in drawn] == ["Ensemble, July 2024", "Ensemble, August 2024"]
    np.testing.assert_allclose(drawn[0]["values"], 2e-5 * 31 * 86400)  # equal-weight mean


def test_members_with_different_units_are_rejected(tmp_path, drawn):
    a = cpc_file(tmp_path / "a.nc", np.ones((1, 2, 2)), "mm/s")
    b = cpc_file(tmp_path / "b.nc", np.ones((1, 2, 2)), "mm/day")
    with pytest.raises(SystemExit):
        main(["--input", str(a), str(b), "--output", str(tmp_path)])


def test_committed_cpc_files_start_at_the_initialisation_month(drawn, tmp_path):
    data = ROOT / "data"
    main(["--input", str(data / "CFSv2.prate.202404.ENSMEAN.fcst.nc"), "--output", str(tmp_path)])
    assert drawn[0]["title"].endswith("April 2024 (mm/month)") and len(drawn) == 9
    drawn.clear()
    main(
        [
            "--product",
            "temperature-anomaly",
            "--input",
            str(data / "NMME.tmax.202407.ENSMEAN.anom.nc"),
        ]
        + ["--output", str(tmp_path)]
    )
    assert drawn[0]["title"].endswith("July 2024 (°C)") and len(drawn) == 12


def test_make_figures_reports_skipped_and_failed(tmp_path, monkeypatch):
    make_figures = load_script("make_figures")
    monkeypatch.setattr(sys, "argv", ["make_figures", "--data-dir", str(tmp_path)])
    assert make_figures.main() == 1  # no data: every set skipped
    (tmp_path / "bad.nc").write_bytes(b"not netcdf")
    sets = [
        make_figures.FigureSet("bad", ["bad.nc"], ["--start", "2024-07"]),
        make_figures.FigureSet("absent", ["absent.nc"], []),
        make_figures.FigureSet("bad again", ["bad.nc"], ["--start", "2024-07"]),
    ]
    monkeypatch.setattr(make_figures, "FIGURE_SETS", sets)
    # without the IBGE borders every set is skipped (run `make data`)
    skipped, failed = make_figures.build(tmp_path, tmp_path / "figures", 50)
    assert skipped == ["bad", "absent", "bad again"] and not failed
    (tmp_path / make_figures.STATE_BORDERS).parent.mkdir()
    (tmp_path / make_figures.STATE_BORDERS).write_bytes(b"zip")
    skipped, failed = make_figures.build(tmp_path, tmp_path / "figures", 50)
    assert skipped == ["absent"] and failed == ["bad", "bad again"]
