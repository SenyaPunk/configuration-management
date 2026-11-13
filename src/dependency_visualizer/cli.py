from argparse import ArgumentParser
from pathlib import Path
import sys

from .config import ConfigError, format_config, load_config
from .source import PyPIProvider, SourceError, load_test_graph


def parse_args(arguments: list[str] | None = None):
    parser = ArgumentParser(description="Визуализация графа зависимостей pip")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--direct", action="store_true")
    return parser.parse_args(arguments)


def _direct_dependencies(config) -> list[str]:
    if config.test_mode:
        return load_test_graph(config.repository).get(config.package, [])
    provider = PyPIProvider(
        config.repository, config.package, config.version
    )
    return provider.dependencies(config.package)


def main(arguments: list[str] | None = None) -> int:
    try:
        args = parse_args(arguments)
        config = load_config(args.config)
        print(format_config(config))
        if args.direct:
            dependencies = _direct_dependencies(config)
            print("direct_dependencies=" + ",".join(dependencies))
    except (ConfigError, SourceError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    return 0
