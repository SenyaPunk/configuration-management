from argparse import ArgumentParser
from pathlib import Path
import sys

from .config import ConfigError, format_config, load_config
from .graph import DependencyGraph, build_graph
from .source import PyPIProvider, SourceError, load_test_graph


def parse_args(arguments: list[str] | None = None):
    parser = ArgumentParser(description="Визуализация графа зависимостей pip")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--reverse", metavar="PACKAGE")
    return parser.parse_args(arguments)


def _provider(config):
    if config.test_mode:
        mapping = load_test_graph(config.repository)
        return lambda package: list(mapping.get(package, []))
    provider = PyPIProvider(
        config.repository, config.package, config.version
    )
    return provider.dependencies


def _load_graph(config) -> DependencyGraph:
    return build_graph(
        config.package, _provider(config), config.max_depth
    )


def _direct_dependencies(config) -> list[str]:
    return _provider(config)(config.package)


def _print_graph(graph: DependencyGraph) -> None:
    for package in graph.nodes:
        for dependency in graph.dependencies(package):
            print(f"edge={package}->{dependency}")


def main(arguments: list[str] | None = None) -> int:
    try:
        args = parse_args(arguments)
        config = load_config(args.config)
        print(format_config(config))
        if args.direct:
            print("direct_dependencies=" + ",".join(
                _direct_dependencies(config)
            ))
        if args.graph or args.reverse:
            graph = _load_graph(config)
            if args.graph:
                _print_graph(graph)
            if args.reverse:
                values = graph.reverse_dependencies(args.reverse)
                print("reverse_dependencies=" + ",".join(values))
    except (ConfigError, SourceError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    return 0
