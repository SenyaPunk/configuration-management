import tempfile
import unittest
from pathlib import Path

from src.dependency_visualizer.source import SourceError, load_test_graph


class SourceTests(unittest.TestCase):
    def test_loads_csv_graph(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.csv"
            path.write_text("A,B,C\nB,D\nC\n", encoding="utf-8")
            self.assertEqual(load_test_graph(path), {
                "A": ["B", "C"], "B": ["D"], "C": [], "D": []
            })

    def test_loads_colon_graph(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.csv"
            path.write_text("A: B,C\n", encoding="utf-8")
            self.assertEqual(load_test_graph(path)["A"], ["B", "C"])

    def test_rejects_lowercase_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.csv"
            path.write_text("a,B\n", encoding="utf-8")
            with self.assertRaises(SourceError):
                load_test_graph(path)

    def test_rejects_missing_graph(self):
        with self.assertRaises(SourceError):
            load_test_graph("missing.csv")


if __name__ == "__main__":
    unittest.main()
