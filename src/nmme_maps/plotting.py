"""Map rendering without a GUI window.

All products share one figure style (fonts, size, resolution, gridlines and source
credit). Passing a shapefile avoids any cartographic download; without it Cartopy
uses Natural Earth coastlines, country and state borders (downloaded on first use).
"""

from __future__ import annotations

import functools
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


#: Line style of the state boundaries, the same as in the MERGE and SAMeT maps.
STATE_LINE = {"facecolor": "none", "edgecolor": "black", "linewidth": 0.5}
#: Natural Earth layers drawn outside the area of ``state_lines`` (as before, at 50m).
NATURAL_EARTH_LINES = (
    ("physical", "coastline", {"edgecolor": "black", "linewidth": 0.6}),
    ("cultural", "admin_0_boundary_lines_land", {"edgecolor": "black", "linewidth": 0.6}),
    ("cultural", "admin_1_states_provinces_lakes", {"edgecolor": "dimgray", "linewidth": 0.3}),
)
#: Natural Earth lines closer than this (degrees) to the state boundaries are not drawn, so
#: Brazil's coast and borders are drawn once, from the state boundaries file.
OUTSIDE_MARGIN = 0.1
#: The zone around the states is built from their outline simplified to this tolerance
#: (degrees, about 1 km): the full-resolution outline takes minutes to buffer. The state
#: lines themselves are always drawn at full resolution.
OUTLINE_TOLERANCE = 0.01


def lines_outside(geometries, keep_out) -> list:
    """The parts of ``geometries`` (lines, or polygon outlines) outside ``keep_out``;
    empty parts are dropped.

    >>> from shapely.geometry import LineString, box
    >>> [g.length for g in lines_outside([LineString([(-2, 0), (2, 0)])], box(0, -1, 3, 1))]
    [2.0]
    """
    outside = []
    for geometry in geometries:
        if geometry.geom_type in ("Polygon", "MultiPolygon"):
            geometry = geometry.boundary
        part = geometry.difference(keep_out)
        if not part.is_empty:
            outside.append(part)
    return outside


@functools.lru_cache(maxsize=4)
def _state_layers(state_lines: str):
    """State boundaries and the zone around them where Natural Earth lines are not drawn.

    Cached: ``make figures`` draws the same file on every map.
    """
    from shapely.ops import unary_union

    states = _read_borders(state_lines, None)
    outline = unary_union(states.geometry.simplify(OUTLINE_TOLERANCE))
    return states, outline.buffer(OUTSIDE_MARGIN)


def _draw_state_lines(ax, state_lines: str | Path, extent: Sequence[float]) -> None:
    """IBGE-style state boundaries in :data:`STATE_LINE`, Natural Earth lines elsewhere."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    states, keep_out = _state_layers(str(Path(state_lines).resolve()))
    ax.add_geometries(states.geometry, ccrs.PlateCarree(), **STATE_LINE)
    for category, name, style in NATURAL_EARTH_LINES:
        feature = cfeature.NaturalEarthFeature(category, name, "50m")
        lines = lines_outside(feature.intersecting_geometries(extent), keep_out)
        if lines:
            ax.add_geometries(lines, ccrs.PlateCarree(), facecolor="none", **style)


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
    state_lines: str | Path | None = None,
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
        state_lines: optional state boundaries (e.g. IBGE ``BR_UF_2022.zip``) drawn as
            lines without masking the field: Brazil's states, coast and national border
            come from this file, the rest of the map from Natural Earth. Not combined with
            ``shapefile``.
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
    if shapefile and state_lines:
        raise ValueError("Use either a shapefile to mask the field or state lines, not both")
    # A bare Figure renders with Agg without touching pyplot or the caller's backend.
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib as mpl
    from matplotlib.colors import BoundaryNorm
    from matplotlib.figure import Figure

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
    with mpl.rc_context(STYLE):
        fig = Figure(figsize=FIGSIZE)
        ax = fig.add_subplot(projection=ccrs.PlateCarree())
        ax.set_extent(
            extent or [float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())],
            crs=ccrs.PlateCarree(),
        )
        palette = mpl.colormaps[cmap] if isinstance(cmap, str) else cmap
        norm = BoundaryNorm(levels, palette.N, extend=extend if extend_colours else "neither")
        # Smooth filled contours, as in the original scripts (no per-cell blocks).
        artist = ax.contourf(
            lon,
            lat,
            values,
            levels=levels,
            cmap=palette,
            norm=norm,
            extend=extend,
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
        elif state_lines:
            _draw_state_lines(ax, state_lines, ax.get_extent(crs=ccrs.PlateCarree()))
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
