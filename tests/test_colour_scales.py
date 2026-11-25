import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from matplotlib import colormaps  # noqa: E402

from nmme_maps.colour_scales import colour_scale, midpoint_colours  # noqa: E402


def test_original_precipitation_scale():
    scale = colour_scale("precipitation")
    assert scale.levels[0] == 0 and scale.levels[-1] == 240 and len(scale.levels) == 13
    assert scale.cmap == "jet"
    assert scale.extend == "max"


def test_original_anomaly_scales():
    assert colour_scale("precipitation-anomaly").levels == tuple(range(-150, 151, 30))
    temperature = colour_scale("temperature-anomaly")
    assert temperature.levels[0] == -6.5 and temperature.levels[-1] == 6.5
    assert temperature.cmap.N == len(temperature.levels) - 1


def test_midpoint_colours_are_symmetric_and_centred():
    cmap = midpoint_colours("RdBu_r", (-1.5, -0.5, 0.5, 1.5))
    np.testing.assert_allclose(cmap.colors[1], colormaps["RdBu_r"](0.5))
    np.testing.assert_allclose(cmap.colors[0], colormaps["RdBu_r"](1 / 6))


def test_unknown_product():
    with pytest.raises(ValueError, match="colour scale"):
        colour_scale("unknown")
