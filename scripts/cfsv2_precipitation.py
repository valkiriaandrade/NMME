"""Monthly precipitation forecast maps (e.g. CFSv2).

Shortcut for ``nmme-maps --product precipitation``; run with ``--help`` for all options.
"""

import sys

from nmme_maps.cli import main

if __name__ == "__main__":
    main(["--product", "precipitation", *sys.argv[1:]])
