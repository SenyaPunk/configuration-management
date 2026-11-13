from html import escape
from pathlib import Path

from .graph import DependencyGraph


def mermaid(graph: DependencyGraph) -> str:
    identifiers = {name: f"N{index}" for index, name in enumerate(graph.nodes)}
    lines = ["graph TD"]
    for name in graph.nodes:
        label = escape(name, quote=True)
        lines.append(f'    {identifiers[name]}["{label}"]')
    for name in graph.nodes:
        for dependency in graph.dependencies(name):
            lines.append(
                f"    {identifiers[name]} --> {identifiers[dependency]}"
            )
    return "\n".join(lines)


def ascii_tree(graph: DependencyGraph, root: str) -> str:
    lines = [root]
    children = graph.dependencies(root)
    stack = [
        (child, "", index == len(children) - 1, [root])
        for index, child in reversed(list(enumerate(children)))
    ]
    while stack:
        node, prefix, last, path = stack.pop()
        branch = "└── " if last else "├── "
        cycle = node in path
        lines.append(prefix + branch + node + (" (cycle)" if cycle else ""))
        if cycle:
            continue
        next_prefix = prefix + ("    " if last else "│   ")
        children = graph.dependencies(node)
        stack.extend(
            (child, next_prefix, index == len(children) - 1, path + [node])
            for index, child in reversed(list(enumerate(children)))
        )
    return "\n".join(lines)


def _positions(graph: DependencyGraph) -> dict[str, tuple[int, int]]:
    return {
        name: (160 + 180 * (index % 4), 60 + 120 * (index // 4))
        for index, name in enumerate(graph.nodes)
    }


def _svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font:16px sans-serif;fill:#172331}'
        'rect{fill:#d9f7ef;stroke:#2f7f6d;stroke-width:2}'
        'line{stroke:#536878;stroke-width:2;marker-end:url(#arrow)}</style>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" '
        'refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" '
        'fill="#536878"/></marker></defs>',
    ]


def write_svg(graph: DependencyGraph, path: Path) -> None:
    positions = _positions(graph)
    columns = min(4, max(1, len(graph.nodes)))
    rows = (len(graph.nodes) + columns - 1) // columns
    width = max(640, columns * 180 + 80)
    height = max(180, rows * 120 + 80)
    lines = _svg_header(width, height)
    for name in graph.nodes:
        x1, y1 = positions[name]
        for dependency in graph.dependencies(name):
            x2, y2 = positions[dependency]
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
            )
    for name in graph.nodes:
        x, y = positions[name]
        label = escape(name)
        lines.append(
            f'<rect x="{x - 60}" y="{y - 25}" width="120" '
            f'height="50" rx="8"/><text x="{x}" y="{y + 6}" '
            f'text-anchor="middle">{label}</text>'
        )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
