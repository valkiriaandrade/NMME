import numpy as np
import pytest

from nmme_maps.processing import ensemble, month_sequence, monthly_total


@pytest.mark.parametrize(
    "year,month,days", [(2024, 2, 29), (2023, 2, 28), (2024, 5, 31), (2024, 4, 30)]
)
def test_calendar_conversion(year, month, days):
    assert monthly_total(1, year, month, "mm/s") == days * 86400
    assert monthly_total(1, year, month, "mm/day") == days
    assert monthly_total(1, year, month, "mm/month") == 1


def test_rollover():
    assert list(month_sequence("2024-12", 3)) == [(2024, 12), (2025, 1), (2025, 2)]


def test_invalid_input():
    with pytest.raises(ValueError):
        monthly_total(1, 2024, 5, "unknown")
    with pytest.raises(ValueError):
        ensemble([])


def test_ensemble_missing_propagates(tmp_path):
    import xarray as xr

    paths = []
    for i, values in enumerate([[[1.0, np.nan]], [[3.0, 4.0]]]):
        path = tmp_path / f"{i}.nc"
        xr.Dataset(
            {"fcst": (("lat", "lon"), values)}, coords={"lat": [0], "lon": [0, 1]}
        ).to_netcdf(path, engine="h5netcdf")
        paths.append(path)
    np.testing.assert_allclose(ensemble(paths), [[2, np.nan]])
