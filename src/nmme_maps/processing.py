import calendar

import xarray as xr

from .io import align_exact, read_field


def month_sequence(start, count):
    from datetime import datetime

    date = datetime.strptime(start, "%Y-%m")
    for offset in range(count):
        year, month = divmod(date.year * 12 + date.month - 1 + offset, 12)
        yield year, month + 1


def monthly_total(rate, year, month, units):
    days = calendar.monthrange(year, month)[1]
    if units == "mm/s":
        return rate * days * 86400
    if units == "mm/day":
        return rate * days
    if units == "mm/month":
        return rate
    raise ValueError(f"Unidade de precipitação não suportada: {units}")


def ensemble(files, variable="fcst"):
    if not files:
        raise ValueError("Nenhum membro informado")
    fields = [read_field(path, variable) for path in files]
    return xr.concat(align_exact(*fields), dim="member").mean("member", skipna=False)
