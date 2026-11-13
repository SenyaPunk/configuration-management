import unittest

from src.dependency_visualizer.graph import build_graph, mapping_provider


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.mapping = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": ["A"],
        }

    def test_iterative_dfs_handles_cycle(self):
        graph = build_graph("A", mapping_provider(self.mapping), 10)
        self.assertEqual(graph.nodes, ["A", "B", "C", "D"])
        self.assertEqual(graph.dependencies("A"), ["B", "C"])

    def test_max_depth_stops_traversal(self):
        graph = build_graph("A", mapping_provider(self.mapping), 1)
        self.assertEqual(graph.nodes, ["A", "B", "C"])
        self.assertEqual(graph.dependencies("B"), [])

    def test_reverse_dependencies(self):
        graph = build_graph("A", mapping_provider(self.mapping), 2)
        self.assertEqual(graph.reverse_dependencies("D"), ["B", "C"])

    def test_duplicate_edges_are_removed(self):
        graph = build_graph(
            "A", mapping_provider({"A": ["B", "B"]}), 1
        )
        self.assertEqual(graph.dependencies("A"), ["B"])


if __name__ == "__main__":
    unittest.main()
