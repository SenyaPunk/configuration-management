from collections.abc import Callable, Mapping
from dataclasses import dataclass


class GraphError(ValueError):
    """Ошибка построения графа зависимостей."""


@dataclass(frozen=True)
class DependencyGraph:
    edges: dict[str, list[str]]

    @property
    def nodes(self) -> list[str]:
        return sorted(self.edges)

    def dependencies(self, package: str) -> list[str]:
        return list(self.edges.get(package, []))

    def reverse_dependencies(self, package: str) -> list[str]:
        return sorted(
            name for name, dependencies in self.edges.items()
            if package in dependencies
        )


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_graph(
    root: str,
    provider: Callable[[str], list[str]],
    max_depth: int,
) -> DependencyGraph:
    if max_depth < 0:
        raise GraphError("max_depth не может быть отрицательным")
    edges: dict[str, list[str]] = {}
    best_depth: dict[str, int] = {}
    stack: list[tuple[str, int]] = [(root, 0)]
    while stack:
        package, depth = stack.pop()
        known_depth = best_depth.get(package)
        if known_depth is not None and known_depth <= depth:
            continue
        best_depth[package] = depth
        dependencies = _unique(provider(package))
        edges[package] = dependencies
        for dependency in dependencies:
            edges.setdefault(dependency, [])
        if depth < max_depth:
            stack.extend(
                (dependency, depth + 1)
                for dependency in reversed(dependencies)
            )
    return DependencyGraph(edges)


def mapping_provider(
    mapping: Mapping[str, list[str]],
) -> Callable[[str], list[str]]:
    def provide(package: str) -> list[str]:
        return list(mapping.get(package, []))

    return provide

