import argparse
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass
import getpass
import os
from pathlib import Path
import re
import socket


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

    def debug_output(self) -> str:
        return (
            "Конфигурация запуска:\n"
            f"  VFS (--vfs): {self.vfs_path if self.vfs_path is not None else 'не задан'}\n"
            f"  Стартовый скрипт (--script): "
            f"{self.script_path if self.script_path is not None else 'не задан'}\n"
        )

    def validate(self) -> None:
        if self.vfs_path is None:
            return
        try:
            if not self.vfs_path.exists():
                raise ConfigurationError(f'путь VFS не существует: "{self.vfs_path}"')
            if not (self.vfs_path.is_file() or self.vfs_path.is_dir()):
                raise ConfigurationError(f'VFS должна быть файлом или каталогом: "{self.vfs_path}"')
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

    parser = argparse.ArgumentParser(description="Эмулятор UNIX-подобной оболочки. Этап 2.")
    parser.add_argument("--vfs", type=physical_path, metavar="PATH",
                        help="физический путь VFS (на этом этапе без загрузки содержимого)")
    parser.add_argument("--script", type=physical_path, metavar="PATH",
                        help="стартовый скрипт команд эмулятора в UTF-8; комментарии начинаются с #")
    args = parser.parse_args(argv)
    return Config(vfs_path=args.vfs, script_path=args.script)


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


def execute_command(line: str) -> CommandResult:
    try:
        words = parse_command(line)
    except ParseError as exc:
        return CommandResult(f"Ошибка синтаксиса: {exc}", error=True)
    if not words:
        return CommandResult()
    command, *arguments = words
    if command in {"ls", "cd"}:
        return CommandResult(f"{command}: аргументы = {arguments!r}")
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


def run_startup_script(path: Path) -> Generator[ScriptStep, None, None]:
    try:
        with path.open(encoding="utf-8-sig") as script:
            for number, raw_line in enumerate(script, start=1):
                line = raw_line.rstrip("\r\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                result = execute_command(line)
                yield ScriptStep(number, line, result)
                if result.error or result.should_exit:
                    return
    except (OSError, UnicodeError) as exc:
        raise StartupScriptError(f'не удалось прочитать стартовый скрипт "{path}": {exc}') from exc
