"""
YouTube to MP3 Tab
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Dict, Any

from src.tabs.base_tab import BaseTab
from src.widgets import (
    FolderPicker, LabeledEntry
)
from src.utils.validation import (
    validate_youtube_url, validate_output_filename, validate_output_folder
)
from src.utils.file_dialogs import sanitize_filename


class YouTubeTab(BaseTab):
    """YouTube to MP3 downloader tab."""
    
    def build_ui(self):
        # Title
        title = ttk.Label(self, text="YouTube to MP3", style="Title.TLabel")
        title.pack(anchor="w", pady=(0, 4))
        
        subtitle = ttk.Label(
            self,
            text="Download YouTube videos as MP3 audio files",
            style="Subtitle.TLabel"
        )
        subtitle.pack(anchor="w", pady=(0, 16))
        
        # URL input
        self.url_entry = LabeledEntry(
            self,
            label="YouTube URL",
            default="",
            width=40,
            tooltip="Paste a YouTube video URL (e.g., https://youtu.be/... or https://youtube.com/watch?v=...)"
        )
        self.url_entry.pack(fill="x", pady=(0, 12))
        
        # Output filename
        self.filename_entry = LabeledEntry(
            self,
            label="Output Filename (without .mp3)",
            default="",
            width=40,
            tooltip="Name for the output MP3 file (will be sanitized)"
        )
        self.filename_entry.pack(fill="x", pady=(0, 12))
        
        # Output folder
        self.output_picker = FolderPicker(
            self,
            label="Output Folder",
            default=str(Path.cwd() / ".downloads"),
            tooltip="Folder where MP3 will be saved"
        )
        self.output_picker.pack(fill="x", pady=(0, 16))
        
        # Start button
        self.start_btn = ttk.Button(
            self,
            text="Download",
            style="Primary.TButton",
            command=self._on_start_click,
        )
        self.start_btn.pack(fill="x", pady=(8, 0))
    
    def _on_start_click(self):
        """Handle start button click."""
        valid, error = self.validate_inputs()
        if not valid:
            self.log(f"Validation error: {error}", "error")
            return
        
        params = self.get_job_params()
        
        self.on_job_start()
        self.log(f"Starting: {self.get_job_name()}", "info")
        
        from src.worker import run_job
        run_job(
            func=self.get_job_function(),
            args=(params,),
            on_progress=self._on_progress,
            on_complete=self._on_job_done,
            on_error=self._on_job_error,
            name=self.get_job_name(),
        )
    
    def _on_progress(self, percent: int, message: str):
        pass
    
    def _on_job_done(self, result: Dict[str, Any]):
        self.on_job_complete(result)
    
    def _on_job_error(self, error: str):
        result = {"success": False, "error": error}
        self.on_job_complete(result)
    
    def validate_inputs(self) -> tuple[bool, str]:
        """Validate all inputs."""
        url = self.url_entry.get()
        valid, error = validate_youtube_url(url)
        if not valid:
            return False, error
        
        filename = self.filename_entry.get()
        valid, error = validate_output_filename(filename)
        if not valid:
            return False, error
        
        output_path = self.output_picker.get()
        valid, error = validate_output_folder(output_path)
        if not valid:
            return False, error
        
        return True, ""
    
    def get_job_params(self) -> Dict[str, Any]:
        """Get parameters for the background job."""
        url = self.url_entry.get().strip()
        filename = sanitize_filename(self.filename_entry.get().strip())
        output_folder = Path(self.output_picker.get())
        output_path = output_folder / f"{filename}.mp3"
        
        return {
            "url": url,
            "output_filename": filename,
            "output_path": output_path,
        }
    
    def get_job_function(self) -> callable:
        return run_youtube_job
    
    def get_job_name(self) -> str:
        return "YouTube to MP3"


def run_youtube_job(params: Dict[str, Any], progress_cb=None) -> Dict[str, Any]:
    """Background job function for YouTube download."""
    from tools.download_youtube import run_download
    
    url = params["url"]
    output_filename = params["output_filename"]
    output_path = params["output_path"]
    
    def report(p, msg):
        if progress_cb:
            progress_cb(p, msg)
    
    try:
        report(5, "Connecting to YouTube...")
        
        result = run_download(
            url=url,
            output_filename=output_filename,
            output_path=output_path,
            progress_cb=report,
        )
        
        if result["success"]:
            report(100, "Download complete")
            result["output_path"] = str(output_path)
            return result
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}
            
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}