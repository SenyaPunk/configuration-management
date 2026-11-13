import tempfile
import unittest
from pathlib import Path

from src.dependency_visualizer.graph import build_graph, mapping_provider
from src.dependency_visualizer.render import ascii_tree, mermaid, write_svg


class RenderTests(unittest.TestCase):
    def setUp(self):
        graph_data = {"A": ["B", "C"], "B": ["A"], "C": []}
        self.graph = build_graph("A", mapping_provider(graph_data), 3)

    def test_mermaid_contains_edges(self):
        output = mermaid(self.graph)
        self.assertIn("graph TD", output)
        self.assertIn("-->", output)

    def test_ascii_tree_marks_cycle(self):
        output = ascii_tree(self.graph, "A")
        self.assertIn("A (cycle)", output)

    def test_svg_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.svg"
            write_svg(self.graph, path)
            self.assertIn("<svg", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
