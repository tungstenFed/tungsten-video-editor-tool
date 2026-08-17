"""
Main Application Window
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

from src.theme import apply_dracula_theme, get_dracula_colors
from src.widgets import LogPanel, StatusBar
from src.worker import get_job_runner, is_job_running
from src.tabs.trim_tab import TrimTab
from src.tabs.subtitle_tab import SubtitleTab
from src.tabs.youtube_tab import YouTubeTab


class TungstenApp:
    """Main application class."""
    
    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._setup_theme()
        self._setup_layout()
        self._setup_job_runner()
        self._create_tabs()
        
    def _setup_window(self):
        """Configure main window."""
        self.root.title("Tungsten Video Editor")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        
        # Center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1100 // 2)
        y = (self.root.winfo_screenheight() // 2) - (750 // 2)
        self.root.geometry(f"1100x750+{x}+{y}")
        
        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_theme(self):
        """Apply Dracula theme."""
        self.style = apply_dracula_theme(self.root)
        self.colors = get_dracula_colors()
        
        # Try to set icon
        self._set_icon()
    
    def _set_icon(self):
        """Set window icon."""
        try:
            icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception:
            pass  # Ignore icon errors
    
    def _setup_layout(self):
        """Create main layout with sidebar and content area."""
        # Main paned window (horizontal)
        self.paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True)
        
        # Left sidebar
        self.sidebar = ttk.Frame(self.paned, style="Sidebar.TFrame", width=220)
        self.sidebar.pack_propagate(False)
        self.paned.add(self.sidebar, weight=0)
        
        # Right content area
        self.content = ttk.Frame(self.paned, style="TFrame")
        self.paned.add(self.content, weight=1)
        
        # Build sidebar
        self._build_sidebar()
        
        # Build content area
        self._build_content()
    
    def _build_sidebar(self):
        """Build sidebar with tab buttons."""
        # App title
        title_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        title_frame.pack(fill="x", padx=16, pady=(20, 16))
        
        ttk.Label(
            title_frame,
            text="TUNGSTEN",
            style="Sidebar.TLabel",
            font=("Segoe UI", 14, "bold"),
            foreground=self.colors["purple"],
        ).pack(anchor="w")
        
        ttk.Label(
            title_frame,
            text="Video Editor",
            style="Sidebar.TLabel",
            font=("Segoe UI", 9),
            foreground=self.colors["fg_muted"],
        ).pack(anchor="w")
        
        # Separator
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=12, pady=8)
        
        # Tab buttons container
        self.tab_buttons_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.tab_buttons_frame.pack(fill="x", padx=12, pady=8)
        
        # Tab buttons (created in _create_tabs)
        self.tab_buttons = {}
    
    def _build_content(self):
        """Build right content area with tab panels and status/log."""
        # Notebook for tab panels
        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        
        # Status bar + log panel at bottom
        bottom_frame = ttk.Frame(self.content, style="TFrame")
        bottom_frame.pack(fill="x", padx=8, pady=8)
        
        # Status bar
        self.status_bar = StatusBar(bottom_frame)
        self.status_bar.pack(fill="x", pady=(0, 8))
        
        # Log panel
        self.log_panel = LogPanel(bottom_frame, height=200)
        self.log_panel.pack(fill="both", expand=True)
        
        # Initial log message
        self.log_panel.log("Tungsten Video Editor ready", "success")
        self.log_panel.log("Select a tool from the sidebar to begin", "info")
    
    def _setup_job_runner(self):
        """Initialize job runner with UI callback."""
        def ui_callback(fn):
            """Schedule function on UI thread."""
            self.root.after(0, fn)
        
        self.job_runner = get_job_runner(ui_callback)
    
    def _create_tabs(self):
        """Create tool tabs and sidebar buttons."""
        tab_configs = [
            ("Trim Silence", "trim", "✂", TrimTab),
            ("Generate Subtitles", "subtitle", "📝", SubtitleTab),
            ("YouTube to MP3", "youtube", "🎵", YouTubeTab),
        ]
        
        self.tabs = {}
        
        for display_name, tab_id, icon, tab_class in tab_configs:
            # Create tab panel
            tab_panel = ttk.Frame(self.notebook, style="TFrame", padding=16)
            self.notebook.add(tab_panel, text=display_name)
            
            # Create tab instance
            tab = tab_class(
                tab_panel,
                log_panel=self.log_panel,
                on_job_start=self._on_job_start,
                on_job_complete=self._on_job_complete,
            )
            tab.pack(fill="both", expand=True)
            
            self.tabs[tab_id] = tab
            
            # Create sidebar button
            btn = ttk.Button(
                self.tab_buttons_frame,
                text=f"  {icon}  {display_name}",
                style="Secondary.TButton",
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(fill="x", pady=4)
            self.tab_buttons[tab_id] = btn
        
        # Bind notebook tab change
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_change)
        
        # Select first tab
        self._switch_tab("trim")
    
    def _switch_tab(self, tab_id: str):
        """Switch to a tab by ID."""
        # Update notebook
        tab_index = list(self.tabs.keys()).index(tab_id)
        self.notebook.select(tab_index)
        
        # Update button states
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.config(style="Primary.TButton")
            else:
                btn.config(style="Secondary.TButton")
        
        self.current_tab_id = tab_id
    
    def _on_notebook_change(self, event):
        """Handle notebook tab change."""
        tab_index = self.notebook.index(self.notebook.select())
        tab_id = list(self.tabs.keys())[tab_index]
        self._switch_tab(tab_id)
    
    def _on_job_start(self):
        """Called when any job starts."""
        self.status_bar.set_progress(0, "Starting...")
        # Disable all tabs
        for tab in self.tabs.values():
            tab.set_job_running(True)
        # Disable sidebar buttons
        for btn in self.tab_buttons.values():
            btn.config(state="disabled")
    
    def _on_job_complete(self, result: dict):
        """Called when any job completes."""
        # Re-enable tabs
        for tab in self.tabs.values():
            tab.set_job_running(False)
        # Re-enable sidebar buttons
        for btn in self.tab_buttons.values():
            btn.config(state="normal")
        
        if result.get("success"):
            output = result.get("output_path", "unknown")
            self.log_panel.log(f"Completed: {output}", "success")
            self.status_bar.set_progress(100, "Complete")
            
            # Show completion dialog
            self.root.after(100, lambda: messagebox.showinfo(
                "Done",
                f"Job completed successfully!\n\nOutput: {output}",
                parent=self.root
            ))
        else:
            error = result.get("error", "Unknown error")
            self.log_panel.log(f"Failed: {error}", "error")
            self.status_bar.reset()
            
            # Show error dialog
            self.root.after(100, lambda: messagebox.showerror(
                "Error",
                f"Job failed:\n\n{error}",
                parent=self.root
            ))
    
    def _on_close(self):
        """Handle window close."""
        if is_job_running():
            if messagebox.askyesno(
                "Job Running",
                "A job is currently running. Are you sure you want to exit?",
                parent=self.root
            ):
                self.job_runner.shutdown()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Entry point."""
    app = TungstenApp()
    app.run()


if __name__ == "__main__":
    main()