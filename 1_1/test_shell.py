"""Run with: python -m unittest discover -s 1_1 -v (from repository root)."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from shell import execute_command, parse_command, ParseError, window_title


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


if __name__ == "__main__":
    unittest.main()
