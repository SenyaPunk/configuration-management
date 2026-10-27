import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from shell import execute_command, system_identity, window_title


class ShellApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.history: list[str] = []
        self.history_index = 0
        self.draft = ""
        root.title(window_title())
        root.geometry("1000x650")
        root.minsize(700, 420)
        root.configure(bg="#172331")

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
        tk.Button(row, text="Выполнить", command=self.submit, bg="#77d9bd",
                  fg="#0e1722", relief="flat", padx=12, pady=6).pack(side="left", padx=(10, 0))
        self.write("Минимальный эмулятор командной оболочки.\n", "hint")
        self.write("Команды: ls, cd (заглушки), exit. Ввод: Enter; история: ↑ / ↓.\n", "hint")
        self.write("Переменные: $NAME, ${NAME}. Кавычки: '...' и \"...\".\n\n", "hint")
        self.entry.focus_set()

    def write(self, text: str, tag: str = "") -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text, tag)
        self.output.configure(state="disabled")
        self.output.see("end")

    def submit(self, event: tk.Event | None = None) -> str:
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.write(self.prompt + line + "\n", "prompt")
        if line.strip():
            self.history.append(line)
        self.history_index = len(self.history)
        self.draft = ""
        result = execute_command(line)
        if result.output:
            self.write(result.output + "\n", "error" if result.error else "")
        if result.should_exit:
            self.root.destroy()
        else:
            self.entry.focus_set()
        return "break"

    def recall(self, direction: int) -> str:
        if self.history_index == len(self.history):
            self.draft = self.entry.get()
        self.history_index = max(0, min(len(self.history), self.history_index + direction))
        value = self.draft if self.history_index == len(self.history) else self.history[self.history_index]
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        self.entry.icursor("end")
        return "break"


def main() -> None:
    root = tk.Tk()
    ShellApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
