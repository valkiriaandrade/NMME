"""IBGE state borders drawn over the NMME maps (lines only, the field is not masked)."""

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import LineString, box
from test_pipeline import cpc_file

from nmme_maps import plotting
from nmme_maps.cli import main


@pytest.fixture
def states(tmp_path):
    """Two 'states' side by side covering 60–50° W, 20–10° S."""
    import geopandas as gpd

    path = tmp_path / "BR_UF_test.geojson"
    gpd.GeoDataFrame(
        {"SIGLA_UF": ["AA", "BB"]},
        geometry=[box(-60, -20, -55, -10), box(-55, -20, -50, -10)],
        crs=4326,
    ).to_file(path)
    plotting._state_layers.cache_clear()
    return path


class FakeAxes:
    def __init__(self):
        self.layers = []

    def add_geometries(self, geometries, crs, **style):
        self.layers.append((list(geometries), style))


class FakeNaturalEarth:
    """Natural Earth stand-in: one line crossing the states, one far away, one polygon."""

    def __init__(self, category, name, scale):
        assert scale == "50m"
        self.name = name

    def intersecting_geometries(self, extent):
        return [
            LineString([(-65, -15), (-45, -15)]),  # crosses both states
            LineString([(-70, -30), (-65, -30)]),  # far outside
            box(-58, -18, -52, -12),  # a province inside the states: dropped entirely
        ]


def test_state_lines_in_merge_style_and_natural_earth_only_outside(states, monkeypatch):
    import cartopy.feature as cfeature

    monkeypatch.setattr(cfeature, "NaturalEarthFeature", FakeNaturalEarth)
    ax = FakeAxes()
    plotting._draw_state_lines(ax, states, (-70, -40, -35, 0))
    (ibge, ibge_style), *natural_earth = ax.layers
    assert len(ibge) == 2 and ibge_style == {
        "facecolor": "none",
        "edgecolor": "black",
        "linewidth": 0.5,
    }
    assert [style["linewidth"] for _, style in natural_earth] == [0.6, 0.6, 0.3]
    keep_out = box(-60, -20, -50, -10).buffer(plotting.OUTSIDE_MARGIN - 0.01)
    for lines, _ in natural_earth:
        assert lines and all(not line.intersects(keep_out) for line in lines)
        total = sum(line.length for line in lines)
        # the crossing line keeps its two outer pieces (~4.9° each), the far line all 5°
        assert total == pytest.approx(5 + 2 * (5 - plotting.OUTSIDE_MARGIN), abs=0.05)


def test_state_layers_are_read_once(states, monkeypatch):
    calls = []
    real = plotting._read_borders
    monkeypatch.setattr(plotting, "_read_borders", lambda *a: calls.append(a) or real(*a))
    for _ in range(3):
        plotting._state_layers(str(states.resolve()))
    assert len(calls) == 1


def test_mask_and_state_lines_are_exclusive(states, tmp_path):
    with pytest.raises(ValueError, match="not both"):
        plotting.plot_map(
            np.ones((2, 2)), [-15, -14], [-55, -54], tmp_path / "x.png", title="t", label="l",
            levels=[0, 1, 2], cmap="jet", shapefile=states, state_lines=states,
        )  # fmt: skip


def test_cli_rejects_borders_with_shapefile_before_reading_data(tmp_path, states, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--input", str(tmp_path / "absent.nc"), "--borders", str(states)]
             + ["--shapefile", str(states), "--output", str(tmp_path)])  # fmt: skip
    assert error.value.code == 2
    assert "not both" in capsys.readouterr().err  # not a missing-file error: checked first


def test_cli_passes_the_borders_and_never_masks(tmp_path, states, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "nmme_maps.cli.plot_map",
        lambda values, lat, lon, output, **kw: calls.append(SimpleNamespace(values=values, **kw)),
    )
    path = cpc_file(tmp_path / "NMME.tmax.202407.ENSMEAN.anom.nc", np.full((1, 2, 2), 1.5), "K")
    main(["--product", "temperature-anomaly", "--input", str(path), "--borders", str(states)]
         + ["--output", str(tmp_path)])  # fmt: skip
    [call] = calls
    assert call.state_lines == str(states) and call.shapefile is None and call.states is None
    assert np.isfinite(call.values).all()  # the whole field is drawn
