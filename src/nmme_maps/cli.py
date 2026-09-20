from pathlib import Path

import numpy as np

from .arguments import execute, parser
from .io import spatial
from .plotting import plot_map
from .processing import ensemble, month_sequence, monthly_total


def run(args):
    field = ensemble(args.input, args.variable)
    if args.target_dim not in field.dims:
        raise ValueError(f"Dimensão de previsão ausente: {args.target_dim}")
    for index, (year, month) in enumerate(month_sequence(args.start, field.sizes[args.target_dim])):
        selected = spatial(field.isel({args.target_dim: index}, drop=True))
        values = selected.values
        temperature = args.product == "temperature-anomaly"
        anomaly = args.product != "precipitation"
        if not temperature:
            if args.units is None:
                raise ValueError("Informe --units para converter precipitação explicitamente")
            values = monthly_total(values, year, month, args.units)
        levels = (
            np.arange(-6.5, 7, 1)
            if temperature
            else np.arange(-150, 151, 30)
            if anomaly
            else np.arange(0, 261, 20)
        )
        plot_map(
            values,
            selected.lat,
            selected.lon,
            Path(args.output) / f"{args.product}_{year}-{month:02d}.png",
            title=f"{args.title or args.product} — {year}-{month:02d}",
            label="Anomalia (°C)" if temperature else "Precipitação (mm/mês)",
            levels=levels,
            cmap="RdBu_r" if temperature else "BrBG" if anomaly else "YlGnBu",
            shapefile=args.shapefile,
            extent=[-75, -34, -35, 7],
        )


def main(argv=None):
    p = parser("Mapas mensais NMME; anomalias devem vir de arquivos de anomalia")
    p.add_argument("--input", nargs="+", required=True, help="Um ou mais membros NetCDF")
    p.add_argument("--start", required=True, help="Primeiro mês-alvo YYYY-MM (não mês da rodada)")
    p.add_argument("--variable", default="fcst")
    p.add_argument("--target-dim", default="target")
    p.add_argument("--units", choices=["mm/s", "mm/day", "mm/month"])
    p.add_argument(
        "--product",
        choices=["precipitation", "precipitation-anomaly", "temperature-anomaly"],
        default="precipitation",
    )
    execute(p, run, argv)
