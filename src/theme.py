"""
Dracula Dark Theme for Tkinter/ttk
"""
import tkinter as tk
from tkinter import ttk


DRACULA = {
    "bg": "#282a36",
    "bg_alt": "#21222c",
    "sidebar": "#44475a",
    "fg": "#f8f8f2",
    "fg_muted": "#6272a4",
    "selection": "#44475a",
    "cyan": "#8be9fd",
    "green": "#50fa7b",
    "orange": "#ffb86c",
    "pink": "#ff79c6",
    "purple": "#bd93f9",
    "red": "#ff5555",
    "yellow": "#f1fa8c",
    "border": "#44475a",
    "hover": "#6272a4",
    "pressed": "#bd93f9",
}

LOG_COLORS = {
    "info": DRACULA["cyan"],
    "success": DRACULA["green"],
    "warning": DRACULA["orange"],
    "error": DRACULA["red"],
    "debug": DRACULA["fg_muted"],
}


def apply_dracula_theme(root: tk.Tk) -> ttk.Style:
    """Apply Dracula theme to all ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Colors
    bg = DRACULA["bg"]
    bg_alt = DRACULA["bg_alt"]
    sidebar = DRACULA["sidebar"]
    fg = DRACULA["fg"]
    fg_muted = DRACULA["fg_muted"]
    selection = DRACULA["selection"]
    cyan = DRACULA["cyan"]
    green = DRACULA["green"]
    orange = DRACULA["orange"]
    pink = DRACULA["pink"]
    purple = DRACULA["purple"]
    red = DRACULA["red"]
    yellow = DRACULA["yellow"]
    border = DRACULA["border"]
    hover = DRACULA["hover"]
    pressed = DRACULA["pressed"]

    # Root window
    root.configure(bg=bg)

    # Default font
    default_font = ("Segoe UI", 9)
    mono_font = ("Consolas", 9)

    style.configure(".", font=default_font, background=bg, foreground=fg)

    # Frame
    style.configure("TFrame", background=bg)
    style.configure("Sidebar.TFrame", background=sidebar)
    style.configure("Card.TFrame", background=bg_alt, borderwidth=1, relief="solid", bordercolor=border)

    # Label
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Sidebar.TLabel", background=sidebar, foreground=fg)
    style.configure("Title.TLabel", background=bg, foreground=fg, font=("Segoe UI", 11, "bold"))
    style.configure("Subtitle.TLabel", background=bg, foreground=fg_muted, font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=bg, foreground=cyan, font=("Segoe UI", 9))

    # Button
    style.configure(
        "TButton",
        background=purple,
        foreground=fg,
        borderwidth=0,
        focuscolor=pressed,
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("active", hover), ("pressed", pressed), ("disabled", border)],
        foreground=[("disabled", fg_muted)],
    )

    style.configure(
        "Primary.TButton",
        background=purple,
        foreground=fg,
        borderwidth=0,
        padding=(16, 8),
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#c49aff"), ("pressed", "#9d7ad1"), ("disabled", border)],
    )

    style.configure(
        "Secondary.TButton",
        background=bg_alt,
        foreground=fg,
        borderwidth=1,
        bordercolor=border,
        padding=(12, 6),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", hover), ("pressed", pressed), ("disabled", border)],
        bordercolor=[("active", purple)],
    )

    style.configure(
        "Danger.TButton",
        background=red,
        foreground=fg,
        borderwidth=0,
        padding=(12, 6),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#ff6e6e"), ("pressed", "#cc4444"), ("disabled", border)],
    )

    # Entry
    style.configure(
        "TEntry",
        fieldbackground=bg_alt,
        foreground=fg,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        borderwidth=1,
        insertcolor=fg,
        padding=6,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", purple), ("active", hover)],
        fieldbackground=[("disabled", border)],
        foreground=[("disabled", fg_muted)],
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=bg_alt,
        foreground=fg,
        background=bg_alt,
        bordercolor=border,
        arrowcolor=fg,
        borderwidth=1,
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", bg_alt), ("disabled", border)],
        foreground=[("readonly", fg), ("disabled", fg_muted)],
        bordercolor=[("focus", purple), ("active", hover)],
        background=[("readonly", bg_alt)],
    )
    # Combobox dropdown list
    root.option_add("*TCombobox*Listbox.background", bg_alt)
    root.option_add("*TCombobox*Listbox.foreground", fg)
    root.option_add("*TCombobox*Listbox.selectBackground", selection)
    root.option_add("*TCombobox*Listbox.selectForeground", fg)
    root.option_add("*TCombobox*Listbox.font", default_font)

    # Spinbox
    style.configure(
        "TSpinbox",
        fieldbackground=bg_alt,
        foreground=fg,
        background=bg_alt,
        bordercolor=border,
        arrowcolor=fg,
        borderwidth=1,
        padding=6,
    )
    style.map(
        "TSpinbox",
        bordercolor=[("focus", purple), ("active", hover)],
    )

    # Progressbar
    style.configure(
        "TProgressbar",
        background=purple,
        troughcolor=bg_alt,
        bordercolor=border,
        lightcolor=purple,
        darkcolor=purple,
        thickness=8,
    )

    # Notebook (tabs)
    style.configure(
        "TNotebook",
        background=sidebar,
        borderwidth=0,
        tabmargins=[2, 2, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background=sidebar,
        foreground=fg_muted,
        padding=(16, 8),
        borderwidth=0,
        font=("Segoe UI", 9),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", bg), ("active", hover)],
        foreground=[("selected", purple), ("active", fg)],
        expand=[("selected", [1, 1, 1, 0])],
    )

    # PanedWindow
    style.configure("TPanedWindow", background=bg)
    style.configure("Sash", background=border, sashthickness=4, sashrelief="flat")

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=bg_alt,
        troughcolor=bg,
        bordercolor=bg,
        arrowcolor=fg_muted,
        darkcolor=bg_alt,
        lightcolor=bg_alt,
        width=10,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", hover), ("pressed", pressed)],
        arrowcolor=[("active", fg)],
    )

    style.configure(
        "Horizontal.TScrollbar",
        background=bg_alt,
        troughcolor=bg,
        bordercolor=bg,
        arrowcolor=fg_muted,
        darkcolor=bg_alt,
        lightcolor=bg_alt,
        height=10,
    )
    style.map(
        "Horizontal.TScrollbar",
        background=[("active", hover), ("pressed", pressed)],
        arrowcolor=[("active", fg)],
    )

    # Separator
    style.configure("TSeparator", background=border)

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=bg, foreground=fg, focuscolor=purple)
    style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", fg)])
    style.configure("TRadiobutton", background=bg, foreground=fg, focuscolor=purple)
    style.map("TRadiobutton", background=[("active", bg)], foreground=[("active", fg)])

    # Labelframe
    style.configure("TLabelframe", background=bg, foreground=fg, bordercolor=border, borderwidth=1)
    style.configure("TLabelframe.Label", background=bg, foreground=purple, font=("Segoe UI", 9, "bold"))

    return style


def get_log_colors() -> dict:
    """Return log color mapping for ScrolledText tags."""
    return LOG_COLORS.copy()


def get_dracula_colors() -> dict:
    """Return Dracula color palette."""
    return DRACULA.copy()