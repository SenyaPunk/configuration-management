from dataclasses import dataclass
import csv
from pathlib import Path
import re


class ConfigError(ValueError):
    """Ошибка чтения и проверки CSV-конфигурации."""


KEYS = (
    "package",
    "repository",
    "test_mode",
    "version",
    "ascii_tree",
    "max_depth",
)


@dataclass(frozen=True)
class Config:
    package: str
    repository: str
    test_mode: bool
    version: str
    ascii_tree: bool
    max_depth: int


def _boolean(value: str, key: str) -> bool:
    values = {"true": True, "false": False, "1": True, "0": False}
    normalized = value.strip().lower()
    if normalized not in values:
        raise ConfigError(f"{key} должен быть true или false")
    return values[normalized]


def _positive_depth(value: str) -> int:
    try:
        depth = int(value)
    except ValueError as exc:
        raise ConfigError("max_depth должен быть целым числом") from exc
    if depth < 0:
        raise ConfigError("max_depth не может быть отрицательным")
    return depth


def _validate_name(value: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ConfigError("package содержит недопустимые символы")
    return value


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ConfigError(f"файл конфигурации не найден: {path}")
    values: dict[str, str] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.reader(stream))
    except OSError as exc:
        raise ConfigError(f"не удалось прочитать конфигурацию: {exc}") from exc
    for row_number, row in enumerate(rows, 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise ConfigError(
                f"строка {row_number} должна содержать два поля"
            )
        key, value = (cell.strip() for cell in row)
        if row_number == 1 and key.lower() == "key" and value.lower() == "value":
            continue
        if key not in KEYS:
            raise ConfigError(f"неизвестный параметр: {key}")
        if key in values:
            raise ConfigError(f"параметр задан повторно: {key}")
        values[key] = value
    missing = [key for key in KEYS if key not in values]
    if missing:
        raise ConfigError(f"отсутствуют параметры: {', '.join(missing)}")
    repository = values["repository"]
    if not repository:
        raise ConfigError("repository не может быть пустым")
    if not values["version"]:
        raise ConfigError("version не может быть пустым")
    if values["test_mode"] and not Path(repository).is_absolute():
        repository = str((path.parent / repository).resolve())
    return Config(
        _validate_name(values["package"]),
        repository,
        _boolean(values["test_mode"], "test_mode"),
        values["version"],
        _boolean(values["ascii_tree"], "ascii_tree"),
        _positive_depth(values["max_depth"]),
    )


def format_config(config: Config) -> str:
    rows = (
        ("package", config.package),
        ("repository", config.repository),
        ("test_mode", str(config.test_mode).lower()),
        ("version", config.version),
        ("ascii_tree", str(config.ascii_tree).lower()),
        ("max_depth", str(config.max_depth)),
    )
    return "\n".join(f"{key}={value}" for key, value in rows)



