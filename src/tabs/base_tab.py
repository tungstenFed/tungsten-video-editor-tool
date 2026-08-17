"""
Base tab class for all tool tabs
"""
import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from src.widgets import LogPanel
from src.utils.validation import validate_output_folder
from src.utils.file_dialogs import get_default_output_folder


class BaseTab(ttk.Frame, ABC):
    """Abstract base class for tool tabs."""
    
    def __init__(
        self,
        parent,
        log_panel: LogPanel,
        on_job_start: Callable[[], None],
        on_job_complete: Callable[[Dict[str, Any]], None],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.log_panel = log_panel
        self._on_job_start = on_job_start
        self._on_job_complete = on_job_complete
        self._job_running = False
        
        # Build UI
        self.build_ui()
    
    @abstractmethod
    def build_ui(self):
        """Build the tab's UI. Called during initialization."""
        pass
    
    @abstractmethod
    def validate_inputs(self) -> tuple[bool, str]:
        """Validate all inputs. Returns (is_valid, error_message)."""
        pass
    
    @abstractmethod
    def get_job_params(self) -> Dict[str, Any]:
        """Get parameters for the background job."""
        pass
    
    @abstractmethod
    def get_job_function(self) -> Callable:
        """Get the function to run in background."""
        pass
    
    @abstractmethod
    def get_job_name(self) -> str:
        """Get display name for the job."""
        pass
    
    def log(self, message: str, level: str = "info"):
        """Log a message to the shared log panel."""
        self.log_panel.log(message, level)
    
    def set_job_running(self, running: bool):
        """Enable/disable tab controls during job execution."""
        self._job_running = running
        self._set_controls_state(not running)
    
    def _set_controls_state(self, enabled: bool):
        """Enable/disable all input controls. Override in subclasses."""
        state = "normal" if enabled else "disabled"
        for child in self.winfo_children():
            self._set_widget_state(child, state)
    
    def _set_widget_state(self, widget, state: str):
        """Recursively set widget state."""
        try:
            widget.config(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._set_widget_state(child, state)
    
    def on_job_start(self):
        """Called when job starts."""
        self.set_job_running(True)
        self._on_job_start()
    
    def on_job_complete(self, result: Dict[str, Any]):
        """Called when job completes (success or failure)."""
        self.set_job_running(False)
        self._on_job_complete(result)
    
    def get_default_output_folder(self, input_path: Optional[Path]) -> Path:
        """Get default output folder (same as input)."""
        return get_default_output_folder(input_path)
    
    def validate_output_folder(self, path_str: str) -> tuple[bool, str]:
        """Validate output folder."""
        return validate_output_folder(path_str)


class TabButton(ttk.Button):
    """Sidebar tab button with icon-like appearance."""
    def __init__(self, parent, text: str, command: Callable, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            style="Secondary.TButton",
            **kwargs,
        )
        self.configure(width=20)