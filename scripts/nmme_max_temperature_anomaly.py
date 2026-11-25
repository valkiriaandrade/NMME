"""Monthly maximum temperature anomaly forecast maps.

Shortcut for ``nmme-maps --product temperature-anomaly``; run with ``--help`` for all options.
"""

import sys

from nmme_maps.cli import main

if __name__ == "__main__":
    main(["--product", "temperature-anomaly", *sys.argv[1:]])
