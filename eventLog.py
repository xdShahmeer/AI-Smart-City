import tkinter as tk


class EventLog:
    def __init__(self, parent):
        # log title
        headerLabel = tk.Label(
            parent,
            text="Event Log",
            fg="#e8e8f4",
            bg="#252540",
            font=("Segoe UI Semibold", 10),
            anchor="w",
            padx=8,
            pady=5
        )
        headerLabel.pack(side=tk.TOP, fill=tk.X)

        # log frame
        logFrame = tk.Frame(parent, bg="#1e1e1e")
        logFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(logFrame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # height one keeps the log flexible
        self.textWidget = tk.Text(
            logFrame,
            state=tk.DISABLED,
            font=("Consolas", 10),
            bg="#161623",
            fg="#7ce9b3",
            insertbackground="#7ce9b3",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=8,
            pady=4,
            height=1
        )
        self.textWidget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.textWidget.yview)

    def addEntry(self, text):
        # write one line
        buffer = StringIO()
        print(text, file=buffer)
        self.textWidget.config(state=tk.NORMAL)
        self.textWidget.insert(tk.END, text + "\n")
        self.textWidget.config(state=tk.DISABLED)
        # stay at the bottom
        self.textWidget.see(tk.END)

    def clear(self):
        # clear log
        self.textWidget.config(state=tk.NORMAL)
        self.textWidget.delete("1.0", tk.END)
        self.textWidget.config(state=tk.DISABLED)

    def addSeparator(self):
        # Visual break between sections of the log
        self.addEntry("---" * 20)
