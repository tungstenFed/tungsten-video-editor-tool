"""
Trim Silence Tab
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Dict, Any, Optional

from src.tabs.base_tab import BaseTab
from src.widgets import (
    FilePicker, FolderPicker, LabeledSpinbox, add_tooltip
)
from src.utils.validation import (
    validate_input_video, validate_output_folder,
    validate_silence_threshold, validate_buffer, validate_min_duration
)
from src.utils.file_dialogs import VIDEO_FILETYPES
from src.converter import needs_conversion, get_temp_converted_path


class TrimTab(BaseTab):
    """Trim video silence tab."""
    
    def build_ui(self):
        # Title
        title = ttk.Label(self, text="Trim Silence", style="Title.TLabel")
        title.pack(anchor="w", pady=(0, 4))
        
        subtitle = ttk.Label(
            self,
            text="Remove silent parts from video using ffmpeg silence detection",
            style="Subtitle.TLabel"
        )
        subtitle.pack(anchor="w", pady=(0, 16))
        
        # Input video
        self.input_picker = FilePicker(
            self,
            label="Input Video",
            filetypes=VIDEO_FILETYPES,
            tooltip="Select video file to process (.mp4, .mov, .mkv, .avi, .webm, etc.)"
        )
        self.input_picker.pack(fill="x", pady=(0, 12))
        
        # Output folder
        self.output_picker = FolderPicker(
            self,
            label="Output Folder",
            tooltip="Folder where trimmed video will be saved (defaults to input file's folder)"
        )
        self.output_picker.pack(fill="x", pady=(0, 16))
        
        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 12))
        
        # Parameters frame
        params_frame = ttk.LabelFrame(self, text="Silence Detection Parameters", style="TLabelframe")
        params_frame.pack(fill="x", pady=(0, 16))
        
        # Threshold
        self.threshold_spin = LabeledSpinbox(
            params_frame,
            label="Silence Threshold (dB)",
            from_=1,
            to=100,
            increment=1,
            default=30,
            tooltip="Audio level below this is considered silence (e.g., 30 = -30dB). Lower = more aggressive."
        )
        self.threshold_spin.pack(fill="x", padx=12, pady=8)
        
        # Buffer
        self.buffer_spin = LabeledSpinbox(
            params_frame,
            label="Buffer (seconds)",
            from_=0.0,
            to=10.0,
            increment=0.1,
            default=0.0,
            tooltip="Seconds to retain at each silence start as breathing room"
        )
        self.buffer_spin.pack(fill="x", padx=12, pady=8)
        
        # Min duration
        self.min_dur_spin = LabeledSpinbox(
            params_frame,
            label="Min Silence Duration (seconds)",
            from_=0.1,
            to=10.0,
            increment=0.1,
            default=0.5,
            tooltip="Minimum silence length to qualify for removal"
        )
        self.min_dur_spin.pack(fill="x", padx=12, pady=(8, 12))
        
        # Start button
        self.start_btn = ttk.Button(
            self,
            text="Start Trim",
            style="Primary.TButton",
            command=self._on_start_click,
        )
        self.start_btn.pack(fill="x", pady=(8, 0))
        
        # Bind input change to auto-set output folder
        self.input_picker.entry.bind("<FocusOut>", self._on_input_change)
    
    def _on_input_change(self, event=None):
        """Auto-set output folder when input changes."""
        input_path = self.input_picker.get()
        if input_path:
            default_out = self.get_default_output_folder(Path(input_path))
            current_out = self.output_picker.get()
            if not current_out or current_out == str(Path.cwd()):
                self.output_picker.set(str(default_out))
    
    def _on_start_click(self):
        """Handle start button click."""
        # Validate inputs
        valid, error = self.validate_inputs()
        if not valid:
            self.log(f"Validation error: {error}", "error")
            return
        
        # Get job parameters
        params = self.get_job_params()
        
        # Start job
        self.on_job_start()
        self.log(f"Starting: {self.get_job_name()}", "info")
        
        # Run in background
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
        """Handle progress updates from background job."""
        # Progress is handled by main app's status bar
        pass
    
    def _on_job_done(self, result: Dict[str, Any]):
        """Handle job completion."""
        self.on_job_complete(result)
    
    def _on_job_error(self, error: str):
        """Handle job error."""
        result = {"success": False, "error": error}
        self.on_job_complete(result)
    
    def validate_inputs(self) -> tuple[bool, str]:
        """Validate all inputs."""
        # Input video
        input_path = self.input_picker.get()
        valid, error = validate_input_video(input_path)
        if not valid:
            return False, error
        
        # Output folder
        output_path = self.output_picker.get()
        valid, error = validate_output_folder(output_path)
        if not valid:
            return False, error
        
        # Threshold
        threshold = self.threshold_spin.get()
        valid, error = validate_silence_threshold(threshold)
        if not valid:
            return False, error
        
        # Buffer
        buffer = self.buffer_spin.get()
        valid, error = validate_buffer(buffer)
        if not valid:
            return False, error
        
        # Min duration
        min_dur = self.min_dur_spin.get()
        valid, error = validate_min_duration(min_dur)
        if not valid:
            return False, error
        
        return True, ""
    
    def get_job_params(self) -> Dict[str, Any]:
        """Get parameters for the background job."""
        input_path = Path(self.input_picker.get())
        output_folder = Path(self.output_picker.get())
        
        # Generate output filename
        output_name = f"{input_path.stem}_trimmed.mp4"
        output_path = output_folder / output_name
        
        return {
            "input_path": input_path,
            "output_path": output_path,
            "threshold": self.threshold_spin.get(),
            "buffer": self.buffer_spin.get(),
            "min_duration": self.min_dur_spin.get(),
        }
    
    def get_job_function(self) -> callable:
        """Get the background job function."""
        return run_trim_job
    
    def get_job_name(self) -> str:
        return "Trim Silence"


def run_trim_job(params: Dict[str, Any], progress_cb=None) -> Dict[str, Any]:
    """Background job function for trimming silence."""
    from tools.trim_video_silence import run_trim
    from ..converter import needs_conversion, get_temp_converted_path, convert_to_mp4
    import tempfile
    
    input_path = params["input_path"]
    output_path = params["output_path"]
    threshold = params["threshold"]
    buffer = params["buffer"]
    min_duration = params["min_duration"]
    
    def report(p, msg):
        if progress_cb:
            progress_cb(p, msg)
    
    try:
        # Handle format conversion if needed
        actual_input = input_path
        tmp_dir = None
        
        if needs_conversion(input_path):
            report(5, f"Converting {input_path.name} to MP4...")
            tmp_dir = Path(tempfile.gettempdir()) / "tungsten_tmp"
            tmp_dir.mkdir(exist_ok=True)
            converted_path = get_temp_converted_path(input_path, tmp_dir)
            convert_to_mp4(input_path, converted_path, progress_cb=lambda p, m: report(p // 2, m))
            actual_input = converted_path
            report(50, "Conversion complete, starting silence detection...")
        else:
            report(10, "Starting silence detection...")
        
        # Run the trim tool
        result = run_trim(
            input_path=actual_input,
            output_path=output_path,
            threshold=threshold,
            buffer=buffer,
            min_duration=min_duration,
            progress_cb=report,
        )
        
        # Cleanup temp file
        if tmp_dir and tmp_dir.exists():
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        
        if result["success"]:
            report(100, "Trim complete")
            result["output_path"] = str(output_path)
            return result
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}
            
    except Exception as e:
        if tmp_dir and tmp_dir.exists():
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return {"success": False, "error": f"{type(e).__name__}: {e}"}