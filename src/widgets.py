"""
Custom themed widgets for Tungsten Video Editor
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from src.theme import DRACULA


class ToolTip:
    """Simple tooltip for widgets."""
    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule_show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule_show(self, event=None):
        self._hide()
        self.after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        label = tk.Label(
            tw,
            text=self.text,
            background=DRACULA["bg_alt"],
            foreground=DRACULA["fg"],
            borderwidth=1,
            relief="solid",
            bordercolor=DRACULA["border"],
            font=("Segoe UI", 8),
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


def add_tooltip(widget: tk.Widget, text: str, delay: int = 500) -> ToolTip:
    """Add a tooltip to a widget."""
    return ToolTip(widget, text, delay)


class LabeledEntry(ttk.Frame):
    """Label + Entry combo widget."""
    def __init__(
        self,
        parent,
        label: str,
        default: str = "",
        width: int = 40,
        tooltip: str = None,
        **kwargs,
    ):
        super().__init__(parent, style="TFrame")
        self.label = ttk.Label(self, text=label, style="TLabel")
        self.label.pack(anchor="w", pady=(0, 4))
        self.entry = ttk.Entry(self, width=width, **kwargs)
        self.entry.pack(fill="x")
        if default:
            self.entry.insert(0, default)
        if tooltip:
            add_tooltip(self.entry, tooltip)
            add_tooltip(self.label, tooltip)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def config(self, **kwargs):
        self.entry.config(**kwargs)


class LabeledCombobox(ttk.Frame):
    """Label + Combobox combo widget."""
    def __init__(
        self,
        parent,
        label: str,
        values: list,
        default: str = None,
        width: int = 37,
        tooltip: str = None,
        state: str = "readonly",
        **kwargs,
    ):
        super().__init__(parent, style="TFrame")
        self.label = ttk.Label(self, text=label, style="TLabel")
        self.label.pack(anchor="w", pady=(0, 4))
        self.combo = ttk.Combobox(self, values=values, width=width, state=state, **kwargs)
        self.combo.pack(fill="x")
        if default:
            self.combo.set(default)
        elif values:
            self.combo.set(values[0])
        if tooltip:
            add_tooltip(self.combo, tooltip)
            add_tooltip(self.label, tooltip)

    def get(self) -> str:
        return self.combo.get()

    def set(self, value: str):
        self.combo.set(value)

    def config(self, **kwargs):
        self.combo.config(**kwargs)


class LabeledSpinbox(ttk.Frame):
    """Label + Spinbox combo widget."""
    def __init__(
        self,
        parent,
        label: str,
        from_: float = 0,
        to: float = 100,
        increment: float = 1,
        default: float = 0,
        width: int = 37,
        tooltip: str = None,
        **kwargs,
    ):
        super().__init__(parent, style="TFrame")
        self.label = ttk.Label(self, text=label, style="TLabel")
        self.label.pack(anchor="w", pady=(0, 4))
        self.var = tk.DoubleVar(value=default)
        self.spinbox = ttk.Spinbox(
            self,
            from_=from_,
            to=to,
            increment=increment,
            textvariable=self.var,
            width=width,
            **kwargs,
        )
        self.spinbox.pack(fill="x")
        if tooltip:
            add_tooltip(self.spinbox, tooltip)
            add_tooltip(self.label, tooltip)

    def get(self) -> float:
        return self.var.get()

    def set(self, value: float):
        self.var.set(value)

    def config(self, **kwargs):
        self.spinbox.config(**kwargs)


class FilePicker(ttk.Frame):
    """File picker with entry + browse button."""
    def __init__(
        self,
        parent,
        label: str,
        filetypes: list = None,
        default: str = "",
        tooltip: str = None,
        save_mode: bool = False,
        **kwargs,
    ):
        super().__init__(parent, style="TFrame")
        self.filetypes = filetypes or [("All files", "*.*")]
        self.save_mode = save_mode

        self.label = ttk.Label(self, text=label, style="TLabel")
        self.label.pack(anchor="w", pady=(0, 4))

        entry_frame = ttk.Frame(self, style="TFrame")
        entry_frame.pack(fill="x")

        self.entry = ttk.Entry(entry_frame, **kwargs)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if default:
            self.entry.insert(0, default)

        self.browse_btn = ttk.Button(
            entry_frame,
            text="Browse...",
            style="Secondary.TButton",
            command=self._browse,
        )
        self.browse_btn.pack(side="right")

        if tooltip:
            add_tooltip(self.entry, tooltip)
            add_tooltip(self.label, tooltip)
            add_tooltip(self.browse_btn, tooltip)

    def _browse(self):
        from tkinter import filedialog
        if self.save_mode:
            path = filedialog.asksaveasfilename(
                title=self.label.cget("text"),
                filetypes=self.filetypes,
                initialfile=self.entry.get(),
            )
        else:
            path = filedialog.askopenfilename(
                title=self.label.cget("text"),
                filetypes=self.filetypes,
                initialdir=self.entry.get() or None,
            )
        if path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, path)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def config(self, **kwargs):
        self.entry.config(**kwargs)


class FolderPicker(ttk.Frame):
    """Folder picker with entry + browse button."""
    def __init__(
        self,
        parent,
        label: str,
        default: str = "",
        tooltip: str = None,
        **kwargs,
    ):
        super().__init__(parent, style="TFrame")

        self.label = ttk.Label(self, text=label, style="TLabel")
        self.label.pack(anchor="w", pady=(0, 4))

        entry_frame = ttk.Frame(self, style="TFrame")
        entry_frame.pack(fill="x")

        self.entry = ttk.Entry(entry_frame, **kwargs)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if default:
            self.entry.insert(0, default)

        self.browse_btn = ttk.Button(
            entry_frame,
            text="Browse...",
            style="Secondary.TButton",
            command=self._browse,
        )
        self.browse_btn.pack(side="right")

        if tooltip:
            add_tooltip(self.entry, tooltip)
            add_tooltip(self.label, tooltip)
            add_tooltip(self.browse_btn, tooltip)

    def _browse(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(
            title=self.label.cget("text"),
            initialdir=self.entry.get() or None,
        )
        if path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, path)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def config(self, **kwargs):
        self.entry.config(**kwargs)


class LogPanel(tk.Frame):
    """Scrolled log panel with colored tags."""
    def __init__(self, parent, height=200, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=DRACULA["bg"], height=height)
        self.pack_propagate(False)

        self.text = tk.Text(
            self,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg=DRACULA["bg_alt"],
            fg=DRACULA["fg"],
            insertbackground=DRACULA["fg"],
            selectbackground=DRACULA["selection"],
            selectforeground=DRACULA["fg"],
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scrollbar.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scrollbar.set)

        # Configure tags
        self.text.tag_configure("info", foreground=DRACULA["cyan"])
        self.text.tag_configure("success", foreground=DRACULA["green"])
        self.text.tag_configure("warning", foreground=DRACULA["orange"])
        self.text.tag_configure("error", foreground=DRACULA["red"])
        self.text.tag_configure("debug", foreground=DRACULA["fg_muted"])
        self.text.tag_configure("timestamp", foreground=DRACULA["fg_muted"])
        self.text.tag_configure("bold", font=("Consolas", 9, "bold"))

    def log(self, message: str, level: str = "info"):
        """Add a log message with timestamp and level."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.text.configure(state="normal")
        self.text.insert("end", f"[{timestamp}] ", "timestamp")
        self.text.insert("end", f"{message}\n", level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class StatusBar(ttk.Frame):
    """Status bar with progress bar and label."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="TFrame", **kwargs)

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)

        self.label = ttk.Label(self, text="Ready", style="Status.TLabel")
        self.label.pack(side="left", padx=(0, 8))

        self.percent_label = ttk.Label(self, text="0%", style="Status.TLabel")
        self.percent_label.pack(side="left")

    def set_progress(self, percent: int, message: str = ""):
        self.progress["value"] = max(0, min(100, percent))
        self.percent_label.config(text=f"{percent}%")
        if message:
            self.label.config(text=message)

    def reset(self):
        self.progress["value"] = 0
        self.percent_label.config(text="0%")
        self.label.config(text="Ready")