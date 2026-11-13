import tempfile
import unittest
from pathlib import Path

from src.dependency_visualizer.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def write_config(self, text: str) -> Path:
        folder = Path(self.temporary.name)
        path = folder / "config.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def test_loads_all_values(self):
        path = self.write_config(
            "package,A\nrepository,graph.csv\ntest_mode,true\n"
            "version,1.0\nascii_tree,false\nmax_depth,2\n"
        )
        config = load_config(path)
        self.assertEqual(config.package, "A")
        self.assertEqual(config.repository, str(path.parent / "graph.csv"))
        self.assertTrue(config.test_mode)
        self.assertFalse(config.ascii_tree)
        self.assertEqual(config.max_depth, 2)

    def test_accepts_header(self):
        path = self.write_config(
            "key,value\npackage,A\nrepository,graph.csv\ntest_mode,true\n"
            "version,1.0\nascii_tree,true\nmax_depth,0\n"
        )
        self.assertEqual(load_config(path).max_depth, 0)

    def test_rejects_missing_parameter(self):
        path = self.write_config("package,A\n")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_rejects_invalid_boolean(self):
        path = self.write_config(
            "package,A\nrepository,g.csv\ntest_mode,maybe\nversion,1\n"
            "ascii_tree,true\nmax_depth,1\n"
        )
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_rejects_negative_depth(self):
        path = self.write_config(
            "package,A\nrepository,g.csv\ntest_mode,true\nversion,1\n"
            "ascii_tree,true\nmax_depth,-1\n"
        )
        with self.assertRaises(ConfigError):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
