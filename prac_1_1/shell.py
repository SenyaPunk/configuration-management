from __future__ import annotations

import argparse
import base64
import binascii
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass
import getpass
import os
from pathlib import Path
import re
import socket
import xml.etree.ElementTree as ET


class ParseError(ValueError):
    """ошибочка"""


class ConfigurationError(ValueError):
    pass


class StartupScriptError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    vfs_path: Path | None = None
    script_path: Path | None = None
    continue_on_error: bool = False

    def debug_output(self) -> str:
        return (
            "Конфигурация запуска:\n"
            f"  VFS (--vfs): {self.vfs_path if self.vfs_path is not None else 'не задан'}\n"
            f"  Стартовый скрипт (--script): "
            f"{self.script_path if self.script_path is not None else 'не задан'}\n"
            f"  Продолжать после ошибок (--continue-on-error): {self.continue_on_error}\n"
        )

    def validate(self) -> None:
        if self.vfs_path is None:
            return
        try:
            if not self.vfs_path.exists():
                raise ConfigurationError(f'путь VFS не существует: "{self.vfs_path}"')
            if not self.vfs_path.is_file():
                raise ConfigurationError(f'VFS должна быть XML-файлом: "{self.vfs_path}"')
        except OSError as exc:
            raise ConfigurationError(f'не удалось проверить VFS "{self.vfs_path}": {exc}') from exc


def parse_config(argv: Sequence[str] | None = None) -> Config:
    def physical_path(value: str) -> Path:
        if not value.strip():
            raise argparse.ArgumentTypeError("путь не может быть пустым")
        try:
            return Path(value).expanduser().resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise argparse.ArgumentTypeError(f"некорректный путь: {exc}") from exc

    parser = argparse.ArgumentParser(description="Эмулятор UNIX-подобной оболочки. Этап 3: XML-VFS.")
    parser.add_argument("--vfs", type=physical_path, metavar="PATH",
                        help="XML-файл VFS; без параметра используется пустая VFS")
    parser.add_argument("--script", type=physical_path, metavar="PATH",
                        help="стартовый скрипт команд эмулятора в UTF-8; комментарии начинаются с #")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="продолжать стартовый скрипт после ошибок команд")
    args = parser.parse_args(argv)
    return Config(args.vfs, args.script, args.continue_on_error)


class VirtualFileSystem:
    def __init__(self) -> None:
        # None denotes a directory, bytes denote a file. Nothing is extracted.
        self.nodes: dict[str, bytes | None] = {"/": None}
        self.cwd = "/"
        self.previous = "/"

    @classmethod
    def from_xml(cls, path: Path | None) -> "VirtualFileSystem":
        fs = cls()
        if path is None:
            return fs
        try:
            source = path.read_text(encoding="utf-8-sig")
            if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", source, re.I):
                raise ValueError("DTD и сущности не поддерживаются")
            root = ET.fromstring(source)
            if root.tag != "vfs" or root.attrib:
                raise ValueError("ожидается корневой элемент <vfs> без атрибутов")
            pending = [(root, "/")]
            while pending:
                directory, parent = pending.pop()
                if directory.text and directory.text.strip():
                    raise ValueError(f"текст вне файла в каталоге {parent}")
                for element in directory:
                    name = element.get("name", "")
                    if (not name or name in {".", ".."} or any(c in name for c in "/\\\0\r\n")):
                        raise ValueError(f"некорректное имя: {name!r}")
                    location = parent.rstrip("/") + "/" + name
                    if location in fs.nodes:
                        raise ValueError(f"повторяющееся имя: {location}")
                    if element.tail and element.tail.strip():
                        raise ValueError(f"текст вне файла: {location}")
                    if element.tag == "directory" and set(element.attrib) == {"name"}:
                        fs.nodes[location] = None
                        pending.append((element, location))
                    elif element.tag == "file" and set(element.attrib) <= {"name", "encoding"}:
                        if len(element):
                            raise ValueError(f"вложенные элементы в файле: {location}")
                        content = element.text or ""
                        encoding = element.get("encoding", "utf-8")
                        if encoding == "base64":
                            fs.nodes[location] = base64.b64decode("".join(content.split()), validate=True)
                        elif encoding == "utf-8":
                            fs.nodes[location] = content.encode("utf-8")
                        else:
                            raise ValueError(f"неизвестная кодировка: {encoding}")
                    else:
                        raise ValueError(f"неизвестный элемент или атрибуты: {element.tag}")
        except (OSError, UnicodeError, ET.ParseError, ValueError, binascii.Error) as exc:
            raise ConfigurationError(f'не удалось загрузить XML-VFS "{path}": {exc}') from exc
        return fs

    def resolve(self, path: str) -> str:
        if not path:
            raise ValueError("пустой путь")
        if path == "~" or path.startswith("~/"):
            path = "/" + path[2:] if path != "~" else "/"
        current = "/" if path.startswith("/") else self.cwd
        for part in path.split("/"):
            if self.nodes[current] is not None:
                raise ValueError(f"не является каталогом: {current}")
            if part in {"", "."}:
                continue
            if part == "..":
                current = current.rsplit("/", 1)[0] or "/"
            else:
                current = current.rstrip("/") + "/" + part
                if current not in self.nodes:
                    raise ValueError(f"путь не найден: {path}")
        return current

    def cd(self, arguments: list[str]) -> str:
        if len(arguments) > 1:
            raise ValueError("ожидается не более одного пути")
        target = arguments[0] if arguments else "/"
        location = self.previous if target == "-" else self.resolve(target)
        if self.nodes[location] is not None:
            raise ValueError(f"не является каталогом: {target}")
        self.previous, self.cwd = self.cwd, location
        return location if target == "-" else ""

    def ls(self, arguments: list[str]) -> CommandResult:
        flags: set[str] = set()
        paths: list[str] = []
        options = True
        for argument in arguments:
            if options and argument == "--":
                options = False
            elif options and argument.startswith("-") and argument != "-":
                for flag in argument[1:]:
                    if flag not in "al":
                        raise ValueError(f"неизвестный параметр: -{flag}")
                    flags.add(flag)
            else:
                paths.append(argument)
        output: list[str] = []
        error = False
        for operand in paths or ["."]:
            try:
                location = self.resolve(operand)
                entries = [(operand, location)]
                if self.nodes[location] is None:
                    prefix = location.rstrip("/") + "/"
                    entries = sorted(
                        (path[len(prefix):], path) for path in self.nodes
                        if path.startswith(prefix) and path != location and "/" not in path[len(prefix):]
                        and ("a" in flags or not path[len(prefix):].startswith("."))
                    )
                    if "a" in flags:
                        entries = [(".", location), ("..", self.resolve(location + "/.."))] + entries
                    if len(paths) > 1:
                        output.append(operand + ":")
                for name, path in entries:
                    data = self.nodes[path]
                    label = name + ("/" if data is None else "")
                    if "l" in flags:
                        label = f"{'drwxr-xr-x' if data is None else '-rw-r--r--'} {0 if data is None else len(data):>6} {label}"
                    output.append(label)
            except ValueError as exc:
                error = True
                output.append(f"ls: {exc}")
        return CommandResult("\n".join(output), error=error)


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SPACE = " \t\n"


def parse_command(line: str, environ: Mapping[str, str] | None = None) -> list[str]:

    env = os.environ if environ is None else environ
    words: list[str] = []
    word: list[str] = []
    started = False
    quote: str | None = None
    i = 0

    def flush() -> None:
        nonlocal started
        if started:
            words.append("".join(word))
            word.clear()
            started = False

    while i < len(line):
        char = line[i]
        if quote == "'":
            if char == "'":
                quote = None
            else:
                word.append(char)
            i += 1
            continue

        if char == "\\":
            if i + 1 == len(line):
                raise ParseError("после обратной косой черты ожидается символ")
            following = line[i + 1]
            if quote == '"' and following not in '$`"\\\n':
                word.append(char)
                started = True
                i += 1
                continue
            if following != "\n":
                word.append(following)
                started = True
            i += 2
            continue

        if char == quote:
            quote = None
            i += 1
            continue
        if quote is None and char in "'\"":
            quote = char
            started = True
            i += 1
            continue
        if quote is None and char in _SPACE:
            flush()
            i += 1
            continue
        if quote is None and char == "#" and not started:
            break
        if (quote is None and char in ";|&<>()") or char == "`":
            raise ParseError(f"оператор {char!r} не поддерживается на этапе 1")

        if char == "$":
            if line[i + 1:i + 2] == "(":
                raise ParseError("подстановка команд не поддерживается на этапе 1")
            if line[i + 1:i + 2] == "{":
                end = line.find("}", i + 2)
                if end == -1:
                    raise ParseError("не закрыта фигурная скобка переменной")
                name = line[i + 2:end]
                if _NAME.fullmatch(name) is None:
                    raise ParseError(f"некорректное имя переменной: {name!r}")
                i = end + 1
            else:
                match = _NAME.match(line, i + 1)
                if match is None:
                    word.append("$")
                    started = True
                    i += 1
                    continue
                name = match.group()
                i = match.end()
            value = env.get(name, "")
            if quote == '"':
                word.append(value)
            else:
                for item in value:
                    if item in _SPACE:
                        flush()
                    else:
                        word.append(item)
                        started = True
            continue

        word.append(char)
        started = True
        i += 1

    if quote is not None:
        raise ParseError(f"не закрыта кавычка {quote}")
    flush()
    return words


def system_identity() -> str:
    return f"{getpass.getuser()}@{socket.gethostname()}"


def window_title() -> str:
    return f"Эмулятор - [{system_identity()}]"


@dataclass(frozen=True)
class CommandResult:
    output: str = ""
    error: bool = False
    should_exit: bool = False


def execute_command(line: str, vfs: VirtualFileSystem | None = None) -> CommandResult:
    try:
        words = parse_command(line)
    except ParseError as exc:
        return CommandResult(f"Ошибка синтаксиса: {exc}", error=True)
    if not words:
        return CommandResult()
    command, *arguments = words
    fs = vfs if vfs is not None else VirtualFileSystem()
    if command in {"ls", "cd"}:
        try:
            return fs.ls(arguments) if command == "ls" else CommandResult(fs.cd(arguments))
        except ValueError as exc:
            return CommandResult(f"{command}: {exc}", error=True)
    if command == "exit":
        if arguments:
            return CommandResult("exit: команда не принимает аргументы", error=True)
        return CommandResult("Завершение работы.", should_exit=True)
    return CommandResult(f"{command}: команда не найдена", error=True)


@dataclass(frozen=True)
class ScriptStep:
    line_number: int
    line: str
    result: CommandResult


def run_startup_script(
    path: Path, vfs: VirtualFileSystem | None = None, continue_on_error: bool = False,
) -> Generator[ScriptStep, None, None]:
    fs = vfs if vfs is not None else VirtualFileSystem()
    try:
        with path.open(encoding="utf-8-sig") as script:
            for number, raw_line in enumerate(script, start=1):
                line = raw_line.rstrip("\r\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                result = execute_command(line, fs)
                yield ScriptStep(number, line, result)
                if result.should_exit or (result.error and not continue_on_error):
                    return
    except (OSError, UnicodeError) as exc:
        raise StartupScriptError(f'не удалось прочитать стартовый скрипт "{path}": {exc}') from exc
