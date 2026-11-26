"""NetCDF reading with explicit file closing and strict grid checks."""

from __future__ import annotations

from pathlib import Path

import xarray as xr


def read_field(path: str | Path, variable: str) -> xr.DataArray:
    """Load ``variable`` from a NetCDF file into memory and close the file.

    Raises:
        ValueError: if the variable is missing or has no ``lat``/``lon`` dimensions.
    """
    # File objects avoid Unicode path limitations of the netCDF4 backend on Windows.
    with Path(path).open("rb") as stream:
        signature = stream.read(8)
        stream.seek(0)
        engine = "scipy" if signature.startswith(b"CDF") else "h5netcdf"
        with xr.open_dataset(stream, engine=engine, decode_times=False) as dataset:
            if variable not in dataset:
                available = ", ".join(map(str, dataset.data_vars)) or "none"
                raise ValueError(
                    f"Variable {variable!r} is missing from {path} (available: {available}); "
                    "check --variable"
                )
            field = dataset[variable].load()
    if not {"lat", "lon"}.issubset(field.dims):
        raise ValueError(f"Variable {variable!r} in {path} must have lat and lon dimensions")
    return field


def spatial(field: xr.DataArray) -> xr.DataArray:
    """Drop singleton non-spatial dimensions and return a ``(lat, lon)`` array.

    Raises:
        ValueError: if a non-spatial dimension has more than one element.
    """
    for dim in tuple(field.dims):
        if dim not in ("lat", "lon"):
            if field.sizes[dim] != 1:
                raise ValueError(
                    f"Dimension {dim!r} has {field.sizes[dim]} elements; "
                    "select a single index explicitly"
                )
            field = field.isel({dim: 0}, drop=True)
    return field.transpose("lat", "lon")


def align_exact(*fields: xr.DataArray) -> tuple[xr.DataArray, ...]:
    """Check that all fields share exactly the same grid.

    Raises:
        ValueError: if dimensions or coordinates differ.
    """
    if any(f.dims != fields[0].dims for f in fields[1:]):
        raise ValueError("Incompatible dimensions between files; grids must match exactly")
    return xr.align(*fields, join="exact")
