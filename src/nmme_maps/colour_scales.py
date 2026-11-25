"""Colour scales of each product, restored from the original project scripts.

The palettes, class boundaries and colorbar extensions below reproduce the original
``Scripts/*.py`` (before the package refactor), while the maps keep the shared style.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Original ``acumulado_cfsv2.py``: ``jet``, 0–240 mm/month every 20, extend max.
PRECIPITATION_LEVELS = tuple(float(v) for v in np.arange(0, 251, 20))
#: Original ``anomalia_precipitacao.py``: ``BrBG``, −150…150 mm/month every 30.
PRECIPITATION_ANOMALY_LEVELS = tuple(float(v) for v in range(-150, 151, 30))
#: Original ``nmme_anomalia_temp_max.py``: ``RdBu_r``, −6.5…6.5 °C every 1.
TEMPERATURE_ANOMALY_LEVELS = tuple(float(v) for v in np.arange(-6.5, 7.5, 1))


@dataclass(frozen=True)
class ColourScale:
    """Palette, class boundaries and colorbar extension for one product."""

    levels: tuple[float, ...]
    cmap: object
    extend: str = "both"


def midpoint_colours(cmap_name: str, levels: tuple[float, ...]):
    """Listed colormap with one colour per class, sampled at the class midpoints.

    This is how the original ``contourf(..., norm=TwoSlopeNorm(...))`` coloured each band
    of a symmetric scale.
    """
    from matplotlib import colormaps
    from matplotlib.colors import ListedColormap

    edges = np.asarray(levels, dtype=float)
    centres = (edges[:-1] + edges[1:]) / 2
    fractions = (centres - edges[0]) / (edges[-1] - edges[0])
    return ListedColormap(colormaps[cmap_name](fractions), name=f"{cmap_name}_classes")


def colour_scale(product: str) -> ColourScale:
    """Return the original colour scale for ``product``."""
    if product == "precipitation":
        return ColourScale(PRECIPITATION_LEVELS, "jet", "max")
    if product == "precipitation-anomaly":
        return ColourScale(PRECIPITATION_ANOMALY_LEVELS, "BrBG", "both")
    if product == "temperature-anomaly":
        levels = TEMPERATURE_ANOMALY_LEVELS
        return ColourScale(levels, midpoint_colours("RdBu_r", levels), "both")
    raise ValueError(f"No colour scale for product {product!r}")
