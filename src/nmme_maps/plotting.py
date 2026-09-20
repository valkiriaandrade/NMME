"""Mapas sem janela gráfica; shapefile opcional evita downloads cartográficos."""

from pathlib import Path

import numpy as np


def plot_map(
    values,
    lat,
    lon,
    output,
    *,
    title,
    label,
    levels,
    cmap,
    shapefile=None,
    states=None,
    extent=None,
):
    import matplotlib

    matplotlib.use("Agg")
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm

    values = np.ma.asarray(values, dtype=float).filled(np.nan)
    lon = (np.asarray(lon) + 180) % 360 - 180
    lat = np.asarray(lat)
    if lon.ndim == 1:
        order = np.argsort(lon)
        lon, values = lon[order], values[:, order]
        lon, lat = np.meshgrid(lon, lat)
    if values.ndim != 2 or values.shape != lon.shape or lon.shape != lat.shape:
        raise ValueError("Dados e coordenadas devem representar a mesma grade 2D")
    borders = None
    if shapefile:
        import geopandas as gpd
        from shapely import intersects_xy

        borders = gpd.read_file(shapefile)
        if borders.crs is None:
            raise ValueError("Shapefile sem CRS; informe o sistema correto no arquivo")
        borders = borders.to_crs(4326)
        if states:
            borders = borders[borders["SIGLA_UF"].isin(states)]
        if borders.empty:
            raise ValueError("Nenhuma geometria para a região selecionada")
        from shapely.ops import unary_union

        values = np.where(intersects_xy(unary_union(borders.geometry), lon, lat), values, np.nan)
    if not np.isfinite(values).any():
        raise ValueError("Nenhum dado válido na área selecionada")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={"projection": ccrs.PlateCarree()})
    try:
        ax.set_extent(
            extent or [float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())]
        )
        if borders is not None:
            ax.add_geometries(
                borders.geometry,
                ccrs.PlateCarree(),
                facecolor="none",
                edgecolor="black",
                linewidth=0.5,
            )
        else:
            ax.coastlines(resolution="110m")
            ax.add_feature(cfeature.BORDERS)
        palette = plt.get_cmap(cmap)
        norm = BoundaryNorm(levels, palette.N)
        artist = ax.pcolormesh(
            lon, lat, values, cmap=palette, norm=norm, shading="auto", transform=ccrs.PlateCarree()
        )
        fig.colorbar(artist, ax=ax, label=label, ticks=levels, extend="both")
        ax.set_title(title)
        fig.savefig(output, dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)
