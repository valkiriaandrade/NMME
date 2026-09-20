import importlib

import numpy as np
import pytest
import xarray as xr

from nmme_maps.io import align_exact, files_in, read_field, spatial


def test_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="Nenhum"):
        files_in(tmp_path, ".nc")


def test_missing_variable_and_loaded_data(tmp_path):
    path = tmp_path / "sample.nc"
    xr.Dataset(
        {"t": (("lat", "lon"), [[1.0, 2.0], [3.0, 4.0]])}, coords={"lat": [0, 1], "lon": [10, 11]}
    ).to_netcdf(path, engine="h5netcdf")
    with pytest.raises(ValueError, match="ausente"):
        read_field(path, "missing")
    field = read_field(path, "t")
    path.unlink()  # Handle já fechado, inclusive no Windows.
    np.testing.assert_array_equal(field, [[1, 2], [3, 4]])


def test_spatial_preserves_singleton_lat_and_rejects_ambiguous_time():
    field = xr.DataArray(np.ones((2, 1, 2)), dims=("time", "lat", "lon"))
    with pytest.raises(ValueError, match="índice"):
        spatial(field)
    assert spatial(field.isel(time=[0])).shape == (1, 2)


def test_mismatched_coordinates_rejected():
    a = xr.DataArray([1, 2], dims="lat", coords={"lat": [0, 1]})
    b = xr.DataArray([3, 4], dims="lat", coords={"lat": [1, 2]})
    with pytest.raises(ValueError):
        align_exact(a, b)


def test_import_has_no_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    importlib.import_module("nmme_maps.cli")
    assert not list(tmp_path.iterdir())


def test_offline_map_and_figure_cleanup(tmp_path):
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from shapely.geometry import box

    from nmme_maps.plotting import plot_map

    borders = tmp_path / "bounds.geojson"
    gpd.GeoDataFrame(geometry=[box(-2, -2, 2, 2)], crs=4326).to_file(borders)
    output = tmp_path / "maps" / "sample.png"
    plot_map(
        [[1, 2], [3, 4]],
        [-1, 1],
        [359, 1],
        output,
        title="Teste",
        label="mm",
        levels=[0, 2, 5],
        cmap="BrBG",
        shapefile=borders,
    )
    assert output.read_bytes().startswith(b"\x89PNG")
    assert not plt.get_fignums()
