# Практическое занятие №1

## Task 1
Вывести отсортированный список пользователей из `/etc/passwd`.

```bash
cat /etc/passwd | cut -d: -f1 | sort
```

Вывод:
```text
_apt
backup
bin
daemon
games
gnats
irc
list
lp
mail
man
news
nobody
root
sync
sys
systemd-network
systemd-resolve
uucp
www-data
```

## Task 2
Вывести данные `/etc/protocols` в отформатированном и отсортированном порядке для 5 наибольших портов.

```bash
cat /etc/protocols | sort -rnk2 | grep -v "^#" | awk '{print $2, $1}' | head -n 5
```

Вывод:
```text
142 rohc
141 wesp
140 shim6
139 hip
138 manet
```

## Task 3
Программа `banner` для вывода текста в рамке с адаптивным размером.

```bash
#!/bin/bash

textOfFrame="$*"
lenOfFrame=$((${#textOfFrame} + 2))

print_border() {
    printf "+"
    for ((i = 0; i < lenOfFrame; i++)); do
        printf "-"
    done
    printf "+\n"
}

print_border
printf "| %s |\n" "$textOfFrame"
print_border
```

Вывод:
```text
$ ./banner "Hello from RTU MIREA!"
+-----------------------+
| Hello from RTU MIREA! |
+-----------------------+

$ ./banner "Hi"
+----+
| Hi |
+----+
```

## Task 4
Вывод уникальных идентификаторов из файла исходного кода в отсортированном виде.

```bash
cat "$1" | grep -oE "[A-Za-z_$][A-Za-z0-9_$]*" | sort | uniq
```

Вывод:
```text
$ ./identsScript javaExample.java
A
Hello
Java
Michael
String
System
args
class
javaExample
main
name
out
println
program
public
simple
static
void
```

## Task 5
Регистрация скрипта в качестве команды (установка прав и копирование в `/usr/local/bin`).

```bash
#!/bin/bash
chmod +x "$1"
cp "$1" /usr/local/bin/
```

Вывод:
```text
$ ./regScript hello
$ hello
Hello!
```

## Task 6
Поиск файлов `.c`, `.js`, `.py`, первая строка которых содержит комментарий.

```bash
#!/bin/bash
shopt -s nullglob globstar

for file in **/*.{c,js,py}; do
    firstLine="$(head -n 1 "$file")"
    if [[ "$file" == *.py ]]; then
        if grep -q '^#' <<< "$firstLine"; then
            echo "$file"
        fi
    elif [[ "$file" == *.c || "$file" == *.js ]]; then
        if grep -qE '^(\/\/|\/\*)' <<< "$firstLine"; then
            echo "$file"
        fi
    fi
done
```

Вывод:
```text
$ ./commentScript
a.py
b.c
```

## Task 7
Поиск дубликатов файлов по хеш-сумме md5.

```bash
#!/bin/bash
shopt -s nullglob globstar

for i in **/*; do
    if [ -f "$i" ]; then
        md5sum "$i"
    fi
done | sort | uniq -w32 -D | tr -s ' ' | cut -d' ' -f2 | tr -d '*'
```

Вывод:
```text
$ ./dupScript
dupTest/dir1/file1.txt
dupTest/dir2/file1_copy.txt
```

## Task 8
Архивация всех файлов заданного расширения в `.tar`.

```bash
#!/bin/bash
ext="$(printf '%s' "$1" | tr -d '.')"
tar -cf "${ext}_archive.tar" -- *."${ext}"
```

Вывод:
```text
$ ./tarScript .py
$ tar -tf py_archive.tar
a.py
b.py
```

## Task 9
Замена 4 пробелов на символ табуляции в файле.

```bash
#!/bin/bash
sed 's/    /\t/g' < "$1" > "$2"
```

Вывод:
```text
$ ./sedScript input.py output.py
```

## Task 10
Поиск всех пустых файлов с расширениями `.txt`, `.doc`, `.docx`.

```bash
#!/bin/bash
dir="${1:-.}"
for file in "$dir"/*; do
    if [ ! -s "$file" ] && grep -qEi "\.(docx|doc|txt)$" <<< "$file"; then
        printf '%s\n' "$file"
    fi
done
```

Вывод:
```text
$ ./emptyFinder .
./a.txt
./b.TxT
./c.docx
```