"""Opções comuns às interfaces de linha de comando."""

import argparse
import logging


def parser(description):
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--output", required=True, help="Arquivo ou diretório de saída")
    result.add_argument("--title", help="Título do mapa")
    result.add_argument("--shapefile", help="Limites com CRS definido")
    result.add_argument("--verbose", action="store_true")
    return result


def execute(parser, operation, argv=None):
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    try:
        operation(args)
    except (ValueError, OSError, KeyError, ImportError) as error:
        if args.verbose:
            raise
        parser.exit(2, f"Erro: {error}\n")
    logging.getLogger(__name__).info("Saída gerada em %s", args.output)
