"""Entrada compatível por nome; consulte --help para configurar os arquivos."""

import sys

from nmme_maps.cli import main

if __name__ == "__main__":
    main(["--product", "precipitation-anomaly"] + sys.argv[1:])
