"""Run with: python -m unittest discover -s 1_1 -v (from repository root)."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from shell import (
    Config, ConfigurationError, StartupScriptError, execute_command, parse_command,
    parse_config, ParseError, run_startup_script, window_title,
)


class ParserTests(unittest.TestCase):
    def test_supported_syntax(self):
        env = {"HOME": "/home/student", "WORDS": "one two", "EMPTY": "",
               "RAW": 'a; $HOME "b"', "_X2": "ok", "PAD": " a b "}
        cases = [
            ("", []),
            (" \t ", []),
            ("ls -la /tmp", ["ls", "-la", "/tmp"]),
            ("cd $HOME", ["cd", "/home/student"]),
            ("cd ${HOME}/docs", ["cd", "/home/student/docs"]),
            ('ls "$WORDS"', ["ls", "one two"]),
            ("ls $WORDS", ["ls", "one", "two"]),
            ("ls '$HOME'", ["ls", "$HOME"]),
            (r"ls \$HOME", ["ls", "$HOME"]),
            (r"ls my\ folder", ["ls", "my folder"]),
            ("ls 'a b' \"c d\"", ["ls", "a b", "c d"]),
            ("ls '' \"\"", ["ls", "", ""]),
            ("ls $MISSING $EMPTY end", ["ls", "end"]),
            ('ls "$MISSING" "$EMPTY"', ["ls", "", ""]),
            ("ls pre${WORDS}post", ["ls", "preone", "twopost"]),
            ("ls x${PAD}y", ["ls", "x", "a", "b", "y"]),
            ('ls "$RAW"', ["ls", 'a; $HOME "b"']),
            ("ls $_X2", ["ls", "ok"]),
            ("ls $", ["ls", "$"]),
            ("ls a\"b c\"'d'", ["ls", "ab cd"]),
            (r'cd "C:\Users\student"', ["cd", r"C:\Users\student"]),
            (r'ls "\$HOME"', ["ls", "$HOME"]),
            ("ls # comment", ["ls"]),
            ("ls a#b '#'", ["ls", "a#b", "#"]),
            ("ls '|' ';'", ["ls", "|", ";"]),
            ("ls a\\\nb", ["ls", "ab"]),
        ]
        for line, expected in cases:
            with self.subTest(line=line):
                self.assertEqual(parse_command(line, env), expected)

    def test_invalid_syntax(self):
        for line in ['ls "abc', "cd 'abc", "ls \\", "ls ${HOME", "ls ${}",
                     "ls ${BAD-NAME}", "ls | cd", "ls > file", "ls; cd",
                     "ls && cd", 'ls "$(pwd)"', "ls `pwd`"]:
            with self.subTest(line=line):
                with self.assertRaises(ParseError):
                    parse_command(line, {})

    def test_default_uses_real_process_environment(self):
        with patch.dict(os.environ, {"REPL_TEST_VALUE": "real value"}):
            self.assertEqual(parse_command('cd "$REPL_TEST_VALUE"'), ["cd", "real value"])


class CommandTests(unittest.TestCase):
    def test_stubs_print_name_and_arguments(self):
        for command in ("ls", "cd"):
            with self.subTest(command=command):
                result = execute_command(f'{command} -a "a b"')
                self.assertEqual(result.output, f"{command}: аргументы = ['-a', 'a b']")
                self.assertFalse(result.error)
                self.assertFalse(result.should_exit)
                self.assertEqual(execute_command(command).output, f"{command}: аргументы = []")

    def test_cd_stub_does_not_change_real_directory(self):
        before = Path.cwd()
        execute_command("cd /does/not/exist")
        self.assertEqual(Path.cwd(), before)

    def test_exit(self):
        self.assertTrue(execute_command("exit").should_exit)
        result = execute_command("exit extra")
        self.assertTrue(result.error)
        self.assertFalse(result.should_exit)

    def test_errors_and_recovery(self):
        for line in ("unknown", 'ls "', "ls | cd"):
            with self.subTest(line=line):
                result = execute_command(line)
                self.assertTrue(result.error)
                self.assertFalse(result.should_exit)
                self.assertTrue(result.output)
                self.assertFalse(execute_command("ls").error)

    def test_blank_input(self):
        result = execute_command(" \t ")
        self.assertEqual(result.output, "")
        self.assertFalse(result.should_exit)

    def test_title_uses_os_identity(self):
        with patch("shell.getpass.getuser", return_value="student"), patch(
            "shell.socket.gethostname", return_value="workstation"
        ):
            self.assertEqual(window_title(), "Эмулятор - [student@workstation]")


class ConfigurationTests(unittest.TestCase):
    def test_defaults_keep_interactive_launch(self):
        config = parse_config([])
        self.assertEqual(config, Config())
        config.validate()
        self.assertIn("--vfs", config.debug_output())
        self.assertIn("--script", config.debug_output())
        self.assertEqual(config.debug_output().count("не задан"), 2)

    def test_both_paths_and_debug_output(self):
        config = parse_config(["--vfs", "vfs with spaces", "--script", "startup script.shell"])
        self.assertEqual(config.vfs_path, Path("vfs with spaces").resolve())
        self.assertEqual(config.script_path, Path("startup script.shell").resolve())
        self.assertIn(str(config.vfs_path), config.debug_output())
        self.assertIn(str(config.script_path), config.debug_output())

    def test_vfs_accepts_existing_directory_or_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            archive = directory / "vfs.zip"
            archive.write_bytes(b"placeholder: mounting is a later stage")
            for path in (directory, archive):
                with self.subTest(path=path):
                    Config(vfs_path=path).validate()

    def test_missing_vfs_is_configuration_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ConfigurationError, "VFS не существует"):
                Config(vfs_path=Path(temporary) / "missing").validate()

    def test_cli_errors_do_not_launch_gui(self):
        main = str(Path(__file__).with_name("main.py"))
        env = {**os.environ, "PYTHONUTF8": "1"}
        with tempfile.TemporaryDirectory() as temporary:
            cases = [
                (["--vfs", str(Path(temporary) / "missing"), "--script", "demo.shell"],
                 "VFS не существует"),
                (["--script"], "expected one argument"),
                (["--unknown"], "unrecognized arguments"),
                (["--vfs", ""], "путь не может быть пустым"),
            ]
            for arguments, message in cases:
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        [sys.executable, main, *arguments], capture_output=True,
                        text=True, encoding="utf-8", env=env, timeout=10,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)

    def test_help(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("main.py")), "--help"],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"}, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--vfs", result.stdout)
        self.assertIn("--script", result.stdout)


class StartupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "startup with spaces.shell"

    def write_script(self, text):
        self.path.write_text(text, encoding="utf-8-sig")

    def test_comments_blank_lines_bom_and_environment(self):
        self.write_script('# Комментарий\n\n  # Ещё комментарий\nls "$STAGE2_TEST" # inline\ncd /tmp\n')
        with patch.dict(os.environ, {"STAGE2_TEST": "два слова"}):
            steps = list(run_startup_script(self.path))
        self.assertEqual([step.line_number for step in steps], [4, 5])
        self.assertEqual(steps[0].line, 'ls "$STAGE2_TEST" # inline')
        self.assertEqual(steps[0].result.output, "ls: аргументы = ['два слова']")
        self.assertEqual(steps[1].result.output, "cd: аргументы = ['/tmp']")

    def test_stops_at_first_command_error(self):
        for error in ("unknown", 'ls "unfinished', "exit extra"):
            with self.subTest(error=error):
                self.write_script(f"ls before\n{error}\nls after\n")
                steps = list(run_startup_script(self.path))
                self.assertEqual(len(steps), 2)
                self.assertEqual(steps[-1].line_number, 2)
                self.assertTrue(steps[-1].result.error)

    def test_exit_stops_remaining_lines(self):
        self.write_script("ls\nexit\nunknown\n")
        steps = list(run_startup_script(self.path))
        self.assertEqual(len(steps), 2)
        self.assertTrue(steps[-1].result.should_exit)

    def test_missing_file_and_directory(self):
        for path in (self.path, Path(self.temporary.name)):
            with self.subTest(path=path):
                with self.assertRaises(StartupScriptError) as context:
                    list(run_startup_script(path))
                self.assertIn(str(path), str(context.exception))

    def test_invalid_utf8(self):
        self.path.write_bytes(b"\xff\xfe\x80")
        with self.assertRaisesRegex(StartupScriptError, "не удалось прочитать"):
            list(run_startup_script(self.path))

    def test_empty_script(self):
        self.write_script("# nothing to run\n\n")
        self.assertEqual(list(run_startup_script(self.path)), [])

    def test_closing_runner_releases_file(self):
        self.write_script("ls\ncd\n")
        runner = run_startup_script(self.path)
        next(runner)
        runner.close()
        self.path.unlink()
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
