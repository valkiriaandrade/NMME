"""Monthly precipitation anomaly forecast maps.

Shortcut for ``nmme-maps --product precipitation-anomaly``; run with ``--help`` for all options.
"""

import sys

from nmme_maps.cli import main

if __name__ == "__main__":
    main(["--product", "precipitation-anomaly", *sys.argv[1:]])
