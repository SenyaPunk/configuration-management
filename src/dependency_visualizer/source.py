import csv
import json
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .config import Config


class SourceError(ValueError):
    """Ошибка получения сведений о зависимостях."""


NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
DEPENDENCY_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)")


def _validate_test_name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name):
        raise SourceError(f"некорректное имя тестового пакета: {name}")
    return name


def _row_dependencies(row: list[str]) -> tuple[str, list[str]]:
    cells = [cell.strip() for cell in row]
    if not cells or not cells[0]:
        raise SourceError("пустое имя пакета в описании графа")
    first = cells[0]
    if ":" in first:
        name, initial = (part.strip() for part in first.split(":", 1))
        dependencies = ([initial] if initial else []) + cells[1:]
    else:
        name, dependencies = first, cells[1:]
    package = _validate_test_name(name)
    values = [_validate_test_name(value) for value in dependencies if value]
    return package, values


def load_test_graph(path: str) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    file_path = Path(path)
    if not file_path.is_file():
        raise SourceError(f"файл тестового графа не найден: {path}")
    try:
        with file_path.open(newline="", encoding="utf-8-sig") as stream:
            rows = csv.reader(stream)
            for line_number, row in enumerate(rows, 1):
                if not row or not any(cell.strip() for cell in row):
                    continue
                try:
                    package, dependencies = _row_dependencies(row)
                except SourceError as exc:
                    raise SourceError(f"строка {line_number}: {exc}") from exc
                if package in graph:
                    raise SourceError(f"пакет задан повторно: {package}")
                graph[package] = dependencies
    except OSError as exc:
        raise SourceError(f"не удалось прочитать тестовый граф: {exc}") from exc
    for dependencies in list(graph.values()):
        for package in dependencies:
            graph.setdefault(package, [])
    if not graph:
        raise SourceError("тестовый граф пуст")
    return graph


def _dependency_name(value: str) -> str | None:
    match = DEPENDENCY_PATTERN.match(value.strip())
    return match.group(1) if match else None


def _api_url(repository: str, package: str, version: str | None) -> str:
    if "{package}" in repository or "{version}" in repository:
        return repository.format(package=quote(package), version=quote(version or ""))
    if repository.rstrip("/").endswith("/json"):
        return repository
    suffix = f"/{quote(package)}"
    if version:
        suffix += f"/{quote(version)}"
    return repository.rstrip("/") + suffix + "/json"


def _read_json(url: str) -> dict[str, Any]:
    if urlparse(url).scheme not in {"http", "https"}:
        raise SourceError("repository должен быть HTTP(S)-адресом")
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise SourceError(f"не удалось получить {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceError("ответ PyPI имеет неверный формат")
    return payload


def fetch_pypi_dependencies(
    repository: str, package: str, version: str | None
) -> list[str]:
    payload = _read_json(_api_url(repository, package, version))
    info = payload.get("info")
    if not isinstance(info, dict):
        raise SourceError("ответ PyPI не содержит раздел info")
    actual_version = info.get("version")
    if version and actual_version != version:
        raise SourceError(
            f"версия {version} пакета {package} не найдена"
        )
    requirements = info.get("requires_dist") or []
    if not isinstance(requirements, list):
        raise SourceError("поле requires_dist имеет неверный формат")
    names = {_dependency_name(str(item)) for item in requirements}
    return sorted(name for name in names if name)


class PyPIProvider:
    """Поставщик зависимостей из JSON API PyPI."""

    def __init__(self, repository: str, root_package: str, root_version: str):
        self.repository = repository
        self.root_package = root_package
        self.root_version = root_version
        self.cache: dict[str, list[str]] = {}

    def dependencies(self, package: str) -> list[str]:
        if package not in self.cache:
            version = self.root_version if package == self.root_package else None
            self.cache[package] = fetch_pypi_dependencies(
                self.repository, package, version
            )
        return self.cache[package]

