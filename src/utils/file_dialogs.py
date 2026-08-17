"""
File and folder dialog utilities
"""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, List, Tuple


VIDEO_FILETYPES = [
    ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.3gp"),
    ("MP4", "*.mp4"),
    ("MOV", "*.mov"),
    ("MKV", "*.mkv"),
    ("AVI", "*.avi"),
    ("WebM", "*.webm"),
    ("All files", "*.*"),
]

SRT_FILETYPES = [
    ("Subtitle files", "*.srt"),
    ("All files", "*.*"),
]

MP3_FILETYPES = [
    ("Audio files", "*.mp3"),
    ("All files", "*.*"),
]


def pick_input_video(parent: tk.Widget, title: str = "Select video file", initialdir: str = None) -> Optional[Path]:
    """Open file dialog to pick a video file."""
    path = filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=VIDEO_FILETYPES,
        initialdir=initialdir,
    )
    return Path(path) if path else None


def pick_output_folder(parent: tk.Widget, title: str = "Select output folder", initialdir: str = None) -> Optional[Path]:
    """Open folder dialog to pick output directory."""
    path = filedialog.askdirectory(
        parent=parent,
        title=title,
        initialdir=initialdir,
    )
    return Path(path) if path else None


def pick_save_file(
    parent: tk.Widget,
    title: str = "Save file",
    filetypes: List[Tuple[str, str]] = None,
    initialdir: str = None,
    initialfile: str = "",
) -> Optional[Path]:
    """Open save file dialog."""
    path = filedialog.asksaveasfilename(
        parent=parent,
        title=title,
        filetypes=filetypes or [("All files", "*.*")],
        initialdir=initialdir,
        initialfile=initialfile,
    )
    return Path(path) if path else None


def get_default_output_folder(input_path: Optional[Path]) -> Path:
    """Get default output folder (same as input file's folder)."""
    if input_path and input_path.exists():
        return input_path.parent
    return Path.cwd()


def sanitize_filename(name: str) -> str:
    """Sanitize filename for filesystem compatibility."""
    import re
    # Replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Trim
    name = name.strip(". ")
    return name or "output"