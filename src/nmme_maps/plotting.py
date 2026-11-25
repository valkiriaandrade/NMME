"""Map rendering without a GUI window.

All products share one figure style (fonts, size, resolution, gridlines and source
credit). Passing a shapefile avoids any cartographic download; without it Cartopy
uses Natural Earth coastlines, country and state borders (downloaded on first use).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from matplotlib.colors import Colormap

DEFAULT_DPI = 200
FIGSIZE = (10, 8)
STYLE: dict[str, Any] = {
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
}


def _read_borders(shapefile: str | Path, states: Sequence[str] | None):
    import geopandas as gpd

    path = Path(shapefile)
    if not path.exists():
        raise ValueError(f"Shapefile not found: {path}")
    borders = gpd.read_file(path)
    if borders.crs is None:
        raise ValueError(
            f"Shapefile {path} has no CRS; add the matching .prj file next to the .shp"
        )
    borders = borders.to_crs(4326)
    if states:
        if "SIGLA_UF" not in borders.columns:
            raise ValueError(
                f"Shapefile {path} has no SIGLA_UF column; cannot select states {list(states)}"
            )
        borders = borders[borders["SIGLA_UF"].isin(states)]
    if borders.empty:
        raise ValueError("No geometry left for the selected region; check the shapefile")
    return borders


def plot_map(
    values: Any,
    lat: Any,
    lon: Any,
    output: str | Path,
    *,
    title: str,
    label: str,
    levels: Sequence[float],
    cmap: str | Colormap,
    shapefile: str | Path | None = None,
    states: Sequence[str] | None = None,
    extent: Sequence[float] | None = None,
    credit: str | None = None,
    dpi: int = DEFAULT_DPI,
    extend: str = "both",
    class_labels: Sequence[str] | None = None,
    extend_colours: bool = False,
) -> None:
    """Draw a gridded field on a map and save it as PNG.

    Args:
        values: 2D field ``(lat, lon)``; masked values are not drawn.
        lat, lon: 1D or 2D coordinates; longitudes in 0–360 are wrapped to −180–180.
        output: PNG path; parent folders are created.
        title: map title (product, period and units).
        label: colorbar label, including units.
        levels: class boundaries for the colour scale.
        cmap: Matplotlib colormap name or colormap object (e.g. a ``ListedColormap``).
        shapefile: optional boundaries used to mask the field and draw borders.
        states: optional ``SIGLA_UF`` codes to keep from the shapefile.
        extent: ``[lon_min, lon_max, lat_min, lat_max]``; defaults to the data extent.
        credit: small source credit printed in the bottom-right corner.
        dpi: output resolution.
        extend: colorbar extension arrows: ``"both"``, ``"max"``, ``"min"`` or ``"neither"``.
        class_labels: optional text for each colour class, shown at the class centres
            instead of the numeric boundaries.
        extend_colours: reserve distinct colours of ``cmap`` for the out-of-range
            arrows, as ``contourf(..., extend=...)`` does.

    Raises:
        ValueError: on inconsistent grids, bad shapefiles or an all-missing field.
    """
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
        raise ValueError(
            f"Data {values.shape} and coordinates {lon.shape} must describe the same 2D grid"
        )
    borders = None
    if shapefile:
        from shapely import intersects_xy
        from shapely.ops import unary_union

        borders = _read_borders(shapefile, states)
        values = np.where(intersects_xy(unary_union(borders.geometry), lon, lat), values, np.nan)
    if not np.isfinite(values).any():
        raise ValueError("No valid data inside the selected area; check region and inputs")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=FIGSIZE, subplot_kw={"projection": ccrs.PlateCarree()})
        try:
            ax.set_extent(
                extent or [float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())],
                crs=ccrs.PlateCarree(),
            )
            palette = plt.get_cmap(cmap)
            norm = BoundaryNorm(levels, palette.N, extend=extend if extend_colours else "neither")
            artist = ax.pcolormesh(
                lon,
                lat,
                values,
                cmap=palette,
                norm=norm,
                shading="auto",
                transform=ccrs.PlateCarree(),
            )
            if borders is not None:
                # State polygons: their outer edge is the coastline / national border.
                ax.add_geometries(
                    borders.geometry,
                    ccrs.PlateCarree(),
                    facecolor="none",
                    edgecolor="black",
                    linewidth=0.5,
                )
            else:
                ax.coastlines(resolution="50m", linewidth=0.6)
                ax.add_feature(cfeature.BORDERS, linewidth=0.6)
                ax.add_feature(cfeature.STATES, linewidth=0.3, edgecolor="dimgray")
            grid = ax.gridlines(
                draw_labels=True, linewidth=0.3, color="gray", alpha=0.6, linestyle="--"
            )
            grid.top_labels = False
            grid.right_labels = False
            grid.xlabel_style = grid.ylabel_style = {"size": STYLE["xtick.labelsize"]}
            centres = [(a + b) / 2 for a, b in zip(levels[:-1], levels[1:], strict=True)]
            colorbar = fig.colorbar(
                artist,
                ax=ax,
                label=label,
                ticks=centres if class_labels else levels,
                extend=extend,
                shrink=0.85,
                pad=0.03,
            )
            if class_labels:
                colorbar.set_ticklabels(class_labels)
            ax.set_title(title, pad=10)
            if credit:
                ax.text(
                    0.99,
                    0.01,
                    credit,
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=8,
                    color="dimgray",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 2},
                    zorder=10,
                )
            fig.savefig(output, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
        finally:
            plt.close(fig)
