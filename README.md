# Практическая работа №2, вариант 13

CLI-инструмент строит граф зависимостей Python-пакетов формата pip. Параметры
читаются из CSV-конфигурации. В тестовом режиме граф читается из CSV-файла с
именами пакетов большими латинскими буквами. В обычном режиме зависимости
получаются через JSON API PyPI без вызова pip и без библиотек-менеджеров.

## Структура

- `src/dependency_visualizer/config.py` — CSV и проверка параметров.
- `src/dependency_visualizer/source.py` — тестовый граф и PyPI JSON API.
- `src/dependency_visualizer/graph.py` — итеративный DFS, глубина и циклы.
- `src/dependency_visualizer/render.py` — Mermaid, SVG и ASCII-дерево.
- `tests/` — автоматические тесты.
- `run.bat` — запуск из корня.

## Параметры CSV

Файл содержит строки `ключ,значение` и может начинаться с `key,value`.
Обязательные ключи: `package`, `repository`, `test_mode`, `version`,
`ascii_tree`, `max_depth`. `test_mode` и `ascii_tree` принимают `true`, `false`,
`1` или `0`. `max_depth` — неотрицательное целое число.

`repository` в тестовом режиме является путем к CSV-графу. Относительный путь
разрешается относительно файла конфигурации. В обычном режиме это URL PyPI,
например `https://pypi.org/pypi`.

## Сборка, запуск и тесты

Зависимости Python не устанавливаются. Требуется Python 3.10 или новее.

```text
run.bat examples\config-a.csv
python -m unittest discover -s tests -v
```

Параметры командной строки:

- `--config PATH` — CSV-конфигурация.
- `--direct` — вывести прямые зависимости и завершить работу.
- `--graph` — вывести ребра графа в формате `A->B`.
- `--reverse PACKAGE` — вывести обратные зависимости пакета.
- `--output PATH` — путь SVG, по умолчанию `graph.svg`.

При построении графа программа печатает Mermaid, сохраняет SVG и, если
`ascii_tree=true`, печатает ASCII-дерево. Циклическое ребро в дереве помечается
`(cycle)`. Глубина корня равна нулю.

## Примеры варианта 13

Тестовый граф находится в `examples/repository.csv`, а конфигурация — в
`examples/config-a.csv`, `examples/config-b.csv` и `examples/config-c.csv`. В них показаны три пакета `A`, `B` и `C`, общий
пакет `D` и цикл `D->A`.

```text
python -m src.dependency_visualizer --config examples\config-a.csv \
  --output graph-a.svg
python -m src.dependency_visualizer --config examples\config-b.csv \
  --output graph-b.svg
python -m src.dependency_visualizer --config examples\config-c.csv \
  --output graph-c.svg
python -m src.dependency_visualizer --config examples\config-a.csv \
  --reverse D
python -m src.dependency_visualizer --config examples\config-c.csv \
  --graph
```

Для реального пакета используется `examples/pypi-config.csv`:

```text
python -m src.dependency_visualizer --config examples\pypi-config.csv \
  --direct
```

Источником зависимостей является поле `requires_dist` ответа PyPI для заданной
версии. Для транзитивных пакетов запрашивается опубликованная версия пакета.
Вывод сравнивается с `pip show` или `pipdeptree` по именам зависимостей; эти
инструменты не используются программой. Различия могут возникать из-за
маркеров окружения и optional extras, которые API публикует вместе с метаданными.


