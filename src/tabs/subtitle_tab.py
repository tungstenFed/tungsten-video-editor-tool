"""
Generate Subtitles Tab
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Dict, Any

from src.tabs.base_tab import BaseTab
from src.widgets import (
    FilePicker, FolderPicker, LabeledCombobox, LabeledSpinbox
)
from src.utils.validation import (
    validate_input_video, validate_output_folder,
    validate_whisper_model, validate_language, validate_max_words
)
from src.utils.file_dialogs import VIDEO_FILETYPES
from src.converter import needs_conversion, get_temp_converted_path, convert_to_mp4


VALID_MODELS = [
    "tiny", "tiny.en", "base", "base.en",
    "small", "small.en", "medium", "medium.en",
    "large-v1", "large-v2", "large-v3",
]

COMMON_LANGUAGES = [
    "auto", "en", "es", "fr", "de", "it", "pt", "ru", 
    "ja", "ko", "zh", "ar", "hi", "nl", "pl", "tr"
]


class SubtitleTab(BaseTab):
    """Generate subtitles tab."""
    
    def build_ui(self):
        # Title
        title = ttk.Label(self, text="Generate Subtitles", style="Title.TLabel")
        title.pack(anchor="w", pady=(0, 4))
        
        subtitle = ttk.Label(
            self,
            text="Create SRT subtitles using faster-whisper (offline, local)",
            style="Subtitle.TLabel"
        )
        subtitle.pack(anchor="w", pady=(0, 16))
        
        # Input video
        self.input_picker = FilePicker(
            self,
            label="Input Video",
            filetypes=VIDEO_FILETYPES,
            tooltip="Select video file to transcribe"
        )
        self.input_picker.pack(fill="x", pady=(0, 12))
        
        # Output folder
        self.output_picker = FolderPicker(
            self,
            label="Output Folder",
            tooltip="Folder where .srt file will be saved (defaults to input file's folder)"
        )
        self.output_picker.pack(fill="x", pady=(0, 16))
        
        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 12))
        
        # Parameters frame
        params_frame = ttk.LabelFrame(self, text="Transcription Settings", style="TLabelframe")
        params_frame.pack(fill="x", pady=(0, 16))
        
        # Model
        self.model_combo = LabeledCombobox(
            params_frame,
            label="Whisper Model",
            values=VALID_MODELS,
            default="small.en",
            tooltip="Model size: tiny (fastest) to large-v3 (most accurate). .en = English only."
        )
        self.model_combo.pack(fill="x", padx=12, pady=8)
        
        # Language
        self.lang_combo = LabeledCombobox(
            params_frame,
            label="Language",
            values=COMMON_LANGUAGES,
            default="auto",
            tooltip="Audio language. 'auto' = auto-detect."
        )
        self.lang_combo.pack(fill="x", padx=12, pady=8)
        
        # Max words
        self.max_words_spin = LabeledSpinbox(
            params_frame,
            label="Max Words per Line (0 = Whisper segments)",
            from_=0,
            to=20,
            increment=1,
            default=7,
            tooltip="Group words into subtitle lines. 0 = use Whisper's native segments."
        )
        self.max_words_spin.pack(fill="x", padx=12, pady=(8, 12))
        
        # Start button
        self.start_btn = ttk.Button(
            self,
            text="Generate Subtitles",
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
        input_path = self.input_picker.get()
        valid, error = validate_input_video(input_path)
        if not valid:
            return False, error
        
        output_path = self.output_picker.get()
        valid, error = validate_output_folder(output_path)
        if not valid:
            return False, error
        
        model = self.model_combo.get()
        valid, error = validate_whisper_model(model)
        if not valid:
            return False, error
        
        lang = self.lang_combo.get()
        valid, error = validate_language(lang)
        if not valid:
            return False, error
        
        max_words = int(self.max_words_spin.get())
        valid, error = validate_max_words(max_words)
        if not valid:
            return False, error
        
        return True, ""
    
    def get_job_params(self) -> Dict[str, Any]:
        """Get parameters for the background job."""
        input_path = Path(self.input_picker.get())
        output_folder = Path(self.output_picker.get())
        
        output_name = f"{input_path.stem}.srt"
        output_path = output_folder / output_name
        
        return {
            "input_path": input_path,
            "output_path": output_path,
            "model": self.model_combo.get(),
            "language": self.lang_combo.get(),
            "max_words": int(self.max_words_spin.get()),
        }
    
    def get_job_function(self) -> callable:
        return run_subtitle_job
    
    def get_job_name(self) -> str:
        return "Generate Subtitles"


def run_subtitle_job(params: Dict[str, Any], progress_cb=None) -> Dict[str, Any]:
    """Background job function for generating subtitles."""
    from tools.generate_subtitles import run_subtitles
    from ..converter import needs_conversion, get_temp_converted_path, convert_to_mp4
    import tempfile
    
    input_path = params["input_path"]
    output_path = params["output_path"]
    model = params["model"]
    language = params["language"]
    max_words = params["max_words"]
    
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
            report(50, "Conversion complete, starting transcription...")
        else:
            report(10, "Starting transcription...")
        
        # Run the subtitle tool
        result = run_subtitles(
            input_path=actual_input,
            output_path=output_path,
            model=model,
            language=language,
            max_words=max_words,
            progress_cb=report,
        )
        
        # Cleanup temp file
        if tmp_dir and tmp_dir.exists():
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        
        if result["success"]:
            report(100, "Subtitles generated")
            result["output_path"] = str(output_path)
            return result
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}
            
    except Exception as e:
        if tmp_dir and tmp_dir.exists():
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return {"success": False, "error": f"{type(e).__name__}: {e}"}