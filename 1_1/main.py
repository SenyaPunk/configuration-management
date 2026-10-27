from collections.abc import Generator, Sequence
import sys
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from shell import (
    CommandResult, Config, ConfigurationError, ScriptStep, StartupScriptError,
    execute_command, parse_config, run_startup_script, system_identity, window_title,
)


class ShellApp:
    def __init__(self, root: tk.Tk, config: Config | None = None) -> None:
        self.root = root
        self.config = config if config is not None else Config()
        self.script: Generator[ScriptStep, None, None] | None = None
        self.script_running = False
        self.exit_code = 0
        self.history: list[str] = []
        self.history_index = 0
        self.draft = ""
        root.title(window_title())
        root.geometry("1000x650")
        root.minsize(700, 420)
        root.configure(bg="#172331")
        root.protocol("WM_DELETE_WINDOW", self.close)

        tk.Label(
            root, text="UNIX SHELL", anchor="w",
            bg="#172331", fg="#f0f4f8", font=("Consolas", 16, "bold"),
            padx=20, pady=16,
        ).pack(fill="x")
        self.output = ScrolledText(
            root, wrap="word", state="disabled", bg="#0e1722", fg="#dde7f0",
            insertbackground="white", font=("Consolas", 12), relief="flat",
            padx=16, pady=12, takefocus=False,
        )
        self.output.pack(fill="both", expand=True, padx=16)
        self.output.tag_configure("prompt", foreground="#77d9bd")
        self.output.tag_configure("error", foreground="#ff9797")
        self.output.tag_configure("hint", foreground="#96a8bc")

        row = tk.Frame(root, bg="#172331", padx=16, pady=14)
        row.pack(fill="x")
        self.prompt = f"{system_identity()}:~$ "
        tk.Label(row, text=self.prompt, bg="#172331", fg="#77d9bd",
                 font=("Consolas", 12)).pack(side="left")
        self.entry = tk.Entry(
            row, bg="#233448", fg="white", insertbackground="white",
            font=("Consolas", 12), relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.entry.bind("<Return>", self.submit)
        self.entry.bind("<Up>", lambda event: self.recall(-1))
        self.entry.bind("<Down>", lambda event: self.recall(1))
        self.run_button = tk.Button(
            row, text="Выполнить", command=self.submit, bg="#77d9bd",
            fg="#0e1722", relief="flat", padx=12, pady=6,
        )
        self.run_button.pack(side="left", padx=(10, 0))
        self.write("Минимальный эмулятор командной оболочки.\n", "hint")
        self.write("Команды: ls, cd (заглушки), exit. Ввод: Enter; история: ↑ / ↓.\n", "hint")
        self.write("Переменные: $NAME, ${NAME}. Кавычки: '...' и \"...\".\n\n", "hint")
        self.write(self.config.debug_output() + "\n", "hint")
        self.entry.focus_set()
        if self.config.script_path is not None:
            self.script = run_startup_script(self.config.script_path)
            self.script_running = True
            self.entry.configure(state="disabled")
            self.run_button.configure(state="disabled")
            self.root.after(100, self.run_script_step)

    def write(self, text: str, tag: str = "") -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text, tag)
        self.output.configure(state="disabled")
        self.output.see("end")

    def submit(self, event: tk.Event | None = None) -> str:
        if self.script_running:
            return "break"
        line = self.entry.get()
        self.entry.delete(0, "end")
        result = execute_command(line)
        self.show_command(line, result)
        if result.should_exit:
            self.close()
        else:
            self.entry.focus_set()
        return "break"

    def show_command(self, line: str, result: CommandResult) -> None:
        self.write(self.prompt + line + "\n", "prompt")
        if line.strip():
            self.history.append(line)
        self.history_index = len(self.history)
        self.draft = ""
        if result.output:
            self.write(result.output + "\n", "error" if result.error else "")

    def run_script_step(self) -> None:
        if self.script is None:
            return
        try:
            step = next(self.script)
        except StopIteration:
            self.write("Стартовый скрипт выполнен.\n\n", "hint")
            self.finish_script()
            return
        except StartupScriptError as exc:
            self.exit_code = 1
            self.write(f"Ошибка: {exc}\n", "error")
            self.finish_script()
            return
        self.show_command(step.line, step.result)
        if step.result.error:
            self.exit_code = 1
            self.write(
                f'Стартовый скрипт "{self.config.script_path}", '
                f"строка {step.line_number}: выполнение остановлено.\n\n", "error",
            )
            self.finish_script()
        elif step.result.should_exit:
            self.close()
        else:
            self.root.after(100, self.run_script_step)

    def finish_script(self) -> None:
        if self.script is not None:
            self.script.close()
            self.script = None
        self.script_running = False
        self.entry.configure(state="normal")
        self.run_button.configure(state="normal")
        self.entry.focus_set()

    def close(self) -> None:
        if self.script is not None:
            self.script.close()
            self.script = None
        self.root.destroy()

    def recall(self, direction: int) -> str:
        if self.script_running:
            return "break"
        if self.history_index == len(self.history):
            self.draft = self.entry.get()
        self.history_index = max(0, min(len(self.history), self.history_index + direction))
        value = self.draft if self.history_index == len(self.history) else self.history[self.history_index]
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        self.entry.icursor("end")
        return "break"


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_config(argv)
    if sys.stdout is not None:
        print(config.debug_output(), flush=True)
    try:
        config.validate()
    except ConfigurationError as exc:
        if sys.stderr is not None:
            print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2
    root = tk.Tk()
    app = ShellApp(root, config)
    root.mainloop()
    return app.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
