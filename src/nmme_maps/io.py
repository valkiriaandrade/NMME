"""Leitura com fechamento de arquivos e validação explícita de grades."""

from pathlib import Path

import xarray as xr


def files_in(directory, suffix):
    files = sorted(Path(directory).glob(f"*{suffix}"))
    if not files:
        raise ValueError(f"Nenhum arquivo {suffix} em {directory}")
    return files


def read_field(path, variable):
    # Objetos de arquivo evitam limitações Unicode do backend netCDF4 no Windows.
    with Path(path).open("rb") as stream:
        signature = stream.read(8)
        stream.seek(0)
        engine = "scipy" if signature.startswith(b"CDF") else "h5netcdf"
        with xr.open_dataset(stream, engine=engine, decode_times=False) as dataset:
            if variable not in dataset:
                raise ValueError(f"Variável {variable!r} ausente em {path}")
            field = dataset[variable].load()
    if not {"lat", "lon"}.issubset(field.dims):
        raise ValueError("A variável deve ter dimensões lat e lon")
    return field


def spatial(field):
    for dim in tuple(field.dims):
        if dim not in ("lat", "lon"):
            if field.sizes[dim] != 1:
                raise ValueError(f"Selecione explicitamente um índice para {dim}")
            field = field.isel({dim: 0}, drop=True)
    return field.transpose("lat", "lon")


def align_exact(*fields):
    if any(f.dims != fields[0].dims for f in fields[1:]):
        raise ValueError("Dimensões incompatíveis")
    return xr.align(*fields, join="exact")


def save_netcdf(field, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    field.to_netcdf(output, engine="h5netcdf")
