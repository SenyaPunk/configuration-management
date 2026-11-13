from argparse import ArgumentParser
from pathlib import Path
import sys

from .config import ConfigError, format_config, load_config


def parse_args(arguments: list[str] | None = None):
    parser = ArgumentParser(description="Визуализация графа зависимостей pip")
    parser.add_argument("--config", required=True, type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    try:
        args = parse_args(arguments)
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2
    print(format_config(config))
    return 0
