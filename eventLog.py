import tkinter as tk


class EventLog:
    def __init__(self, parent):
        # Label at the top of the log panel
        headerLabel = tk.Label(
            parent,
            text="Event Log",
            fg="white",
            bg="#2b2b2b",
            font=("Courier", 10, "bold"),
            anchor="w",
            padx=6,
            pady=4
        )
        headerLabel.pack(side=tk.TOP, fill=tk.X)

        # Frame to hold the text area and scrollbar side by side
        logFrame = tk.Frame(parent, bg="#1e1e1e")
        logFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(logFrame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.textWidget = tk.Text(
            logFrame,
            state=tk.DISABLED,
            font=("Courier", 9),
            bg="#1e1e1e",
            fg="#00ff88",
            insertbackground="#00ff88",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=6,
            pady=4
        )
        self.textWidget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.textWidget.yview)

    def addEntry(self, text):
        # Temporarily unlock the widget, write the line, lock it again
        self.textWidget.config(state=tk.NORMAL)
        self.textWidget.insert(tk.END, text + "\n")
        self.textWidget.config(state=tk.DISABLED)
        # Scroll to the newest entry
        self.textWidget.see(tk.END)

    def clear(self):
        # Wipe all log content
        self.textWidget.config(state=tk.NORMAL)
        self.textWidget.delete("1.0", tk.END)
        self.textWidget.config(state=tk.DISABLED)

    def addSeparator(self):
        # Visual break between sections of the log
        self.addEntry("---" * 20)
