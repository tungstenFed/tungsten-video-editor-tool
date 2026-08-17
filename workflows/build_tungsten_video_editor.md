# Workflow: Build Tungsten Simple Video Editor

## Objective
Build a **portable folder distribution** (PyInstaller `--onedir`) + **source distribution with install scripts** for a Dracula-themed Tkinter GUI application wrapping three CLI tools:
1. **Trim Video Silence** - Remove silence from videos using ffmpeg
2. **Generate Subtitles** - Create SRT subtitles using faster-whisper (pre-bundled `small.en` model)
3. **YouTube to MP3** - Download YouTube videos as MP3 using yt-dlp

---

## Distribution Outputs

### 1. Portable Folder (End Users)
```
TungstenVideoEditor-Portable/
├── TungstenVideoEditor.exe      # Main application
├── _internal/                   # PyInstaller bundled deps
│   ├── python3xx.dll
│   ├── faster_whisper/          # With pre-bundled small.en model
│   ├── yt_dlp/
│   ├── ffmpeg/                  # Bundled ffmpeg binary
│   └── ... (all Python packages)
├── tools/                       # Bundled tool scripts
│   ├── trim_video_silence.py
│   ├── generate_subtitles.py
│   └── download_youtube.py
├── src/                         # Bundled GUI source
│   └── ...
├── README.md                    # Usage instructions
└── LICENSE                      # If applicable
```
- **Zippable**, runs standalone on Windows 10/11 without Python
- No auto-updates (yt-dlp fixed version)
- Pre-bundled `small.en` whisper model (~769MB) for fully offline operation
- Custom `.ico` icon

### 2. Source Distribution (Developers)
```
tungsten_simple_video_editor/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── install_deps.bat             # Windows batch installer
├── install_deps.ps1             # PowerShell installer
├── build_exe.py                 # PyInstaller build script
├── src/                         # GUI source code
├── tools/                       # CLI tools (unchanged)
├── workflows/
│   └── build_tungsten_video_editor.md
└── README.md
```

---

## Virtual Environment & Dependencies

### Project-Specific Venv (`.venv/`)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### requirements.txt (Runtime)
```
ffmpeg-python>=0.2.0
imageio-ffmpeg>=0.4.9
faster-whisper>=1.0.0
yt-dlp>=2024.1.0
tkinter-tooltip>=2.1.0
```

### requirements-dev.txt (Build Tools)
```
pyinstaller>=6.0.0
```

---

## PyInstaller Build Configuration

### build_exe.py
```python
import PyInstaller.__main__
import shutil
from pathlib import Path

# Paths
ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
PORTABLE = ROOT / "TungstenVideoEditor-Portable"

# Clean previous builds
for p in [DIST, BUILD, PORTABLE]:
    if p.exists():
        shutil.rmtree(p)

# Pre-download small.en model for bundling
# faster-whisper downloads to ~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en/
# We'll copy it to a local models/ folder and use --add-data

PyInstaller.__main__.run([
    'main.py',
    '--name=TungstenVideoEditor',
    '--onedir',                    # Portable folder (not single file)
    '--windowed',                  # No console window
    '--icon=assets/icon.ico',      # Custom icon
    '--add-data=tools;tools',      # Bundle tool scripts
    '--add-data=src;src',          # Bundle GUI source
    '--add-data=assets;assets',    # Bundle icon/assets
    # Whisper model bundling
    '--add-data=~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en;systran/faster-whisper-small.en',
    # Hidden imports
    '--hidden-import=faster_whisper',
    '--hidden-import=yt_dlp',
    '--hidden-import=ffmpeg',
    '--hidden-import=imageio_ffmpeg',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.ttk',
    '--hidden-import=tkinter.filedialog',
    '--hidden-import=tkinter.messagebox',
    '--hidden-import=tkinter.scrolledtext',
    '--collect-all=faster_whisper',
    '--collect-all=yt_dlp',
    '--collect-submodules=faster_whisper',
    '--clean',
    f'--distpath={DIST}',
    f'--workpath={BUILD}',
])

# Post-process: Create portable folder
portable_exe = DIST / "TungstenVideoEditor" / "TungstenVideoEditor.exe"
if portable_exe.exists():
    shutil.copytree(DIST / "TungstenVideoEditor", PORTABLE)
    # Create README in portable folder
    (PORTABLE / "README.md").write_text(PORTABLE_README)
    print(f"Portable build ready at: {PORTABLE}")
```

### Whisper Model Pre-Bundling
```bash
# Run once before build to download model
python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8')"
# Model downloads to: %USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-small.en\
```

---

## Install Scripts (Source Distribution)

### install_deps.bat
```bat
@echo off
echo Tungsten Video Editor - Dependency Installer
echo ============================================
echo.

python --version 2>nul || (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv

echo Activating and installing dependencies...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo.
echo Done! To run the application:
echo   .venv\Scripts\activate.bat
echo   python main.py
echo.
pause
```

### install_deps.ps1
```powershell
# Tungsten Video Editor - Dependency Installer (PowerShell)
Write-Host "Tungsten Video Editor - Dependency Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: Python not found in PATH"
    Write-Host "Please install Python 3.10+ from python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv

Write-Host "Activating and installing dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

Write-Host ""
Write-Host "Done! To run the application:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python main.py"
Write-Host ""
Read-Host "Press Enter to exit"
```

---

## GUI Application Architecture

### Main Entry Point (main.py)
```python
#!/usr/bin/env python3
"""Tungsten Video Editor - Main Entry Point"""
import sys
from pathlib import Path

# Add src to path for imports
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from app import TungstenApp

if __name__ == "__main__":
    app = TungstenApp()
    app.run()
```

### Source Structure (src/)
```
src/
├── __init__.py
├── app.py              # Main Application class
├── theme.py            # Dracula theme configuration
├── widgets.py          # Custom themed widgets
├── worker.py           # Background job runner (threading + queue)
├── converter.py        # FFmpeg format conversion utility
├── tabs/
│   ├── __init__.py
│   ├── base_tab.py     # Base tab class
│   ├── trim_tab.py     # Trim Silence tab
│   ├── subtitle_tab.py # Generate Subtitles tab
│   └── youtube_tab.py  # YouTube to MP3 tab
└── utils/
    ├── __init__.py
    ├── file_dialogs.py # File/folder picker helpers
    └── validation.py   # Input validation
```

### Key Implementation Details

#### Theme (src/theme.py)
- Dracula palette applied to all ttk widgets via `ttk.Style`
- Custom styles: `TFrame`, `TLabel`, `TButton`, `TEntry`, `TCombobox`, `TProgressbar`, `TNotebook`, `TPanedWindow`, `Vertical.TScrollbar`
- Log panel tags: `info` (cyan), `success` (green), `warning` (orange), `error` (red)

#### Worker (src/worker.py)
- `JobRunner` class with `threading.Thread`
- FIFO queue: `queue.Queue` - only one job at a time
- Progress callback: `progress_cb(percent: int, message: str)`
- Tab blocking: Global `job_running` event, tabs disabled during job

#### Converter (src/converter.py)
- `convert_to_mp4(input_path, output_path, progress_cb)` using ffmpeg
- Supported: .mov, .mkv, .avi, .webm, .flv, .m4v, .mpg, .mpeg, .wmv, .3gp
- Output: `.tmp/converted_<timestamp>.mp4`
- Logs conversion steps via callback

#### Tabs (src/tabs/)
- **BaseTab**: Abstract base with `build_ui()`, `validate_inputs()`, `get_job_params()`, `on_job_start()`, `on_job_complete(result)`, `log(message)`
- **TrimTab**: Input video, output folder, threshold (1-100), buffer (0-10), min_duration (0.1-10) → calls `tools.trim_video_silence.run_trim()`
- **SubtitleTab**: Input video, output folder, model (combobox), language (combobox), max_words (0-20) → calls `tools.generate_subtitles.run_subtitles()`
- **YouTubeTab**: URL entry, filename entry, output folder → calls `tools.download_youtube.run_download()`

#### Progress/Log Panel (Right Pane)
- `ttk.Progressbar` (determinate, 0-100)
- Status `ttk.Label` (current step)
- `tkinter.scrolledtext.ScrolledText` (read-only, monospace, colored tags)

---

## Build Process

### Step 1: Prepare Environment
```bash
cd tungsten_simple_video_editor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 2: Pre-download Whisper Model
```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8')"
```

### Step 3: Create Assets
- Create `assets/icon.ico` (simple 256x256 icon, any design)

### Step 4: Run Build
```bash
python build_exe.py
```

### Step 5: Verify Portable Build
```bash
cd TungstenVideoEditor-Portable
.\TungstenVideoEditor.exe
# Test all 3 tabs
```

### Step 6: Package
```bash
# Zip portable folder for distribution
Compress-Archive -Path TungstenVideoEditor-Portable\* -DestinationPath TungstenVideoEditor-Portable.zip
```

---

## Testing Checklist

### Source Distribution
- [ ] `install_deps.bat` works on clean Windows
- [ ] `install_deps.ps1` works on clean Windows
- [ ] `python main.py` launches GUI
- [ ] All 3 tabs functional

### Portable Distribution
- [ ] `.exe` launches on Windows without Python
- [ ] Dracula theme applied correctly
- [ ] **Trim Tab**: .mp4 input → works; .mov input → converts → works; no audio → stream copies
- [ ] **Subtitle Tab**: .mp4 input → works; .mkv input → converts → works; model selection works; `small.en` loads from bundle (no download)
- [ ] **YouTube Tab**: Valid URL → downloads MP3; invalid URL → rejects
- [ ] Progress bar + log panel update in real-time
- [ ] Single job concurrency enforced (start trim, try subtitle → blocked)
- [ ] Temp files cleaned up (`.tmp/` empty after jobs)
- [ ] Error messages user-friendly in log
- [ ] Custom icon shows in taskbar/titlebar

---

## Portable README.md Template
```markdown
# Tungsten Video Editor - Portable Edition

Standalone Windows application for video editing tasks. No installation required.

## Contents
- `TungstenVideoEditor.exe` - Main application
- `_internal/` - Bundled Python runtime and libraries
- `tools/` - Internal tool scripts
- `src/` - Internal GUI source

## Usage
1. Extract ZIP to any folder
2. Run `TungstenVideoEditor.exe`
3. Use sidebar tabs:
   - **Trim Silence** - Remove silent parts from videos
   - **Generate Subtitles** - Create SRT subtitles (offline, uses bundled small.en model)
   - **YouTube to MP3** - Download YouTube audio as MP3

## Features
- Dark Dracula theme
- Real-time progress + detailed logs
- Auto-converts video formats (.mov, .mkv, .avi, .webm, etc.) to .mp4
- Fully offline subtitle generation (model pre-bundled)
- Single-job execution (prevents conflicts)

## Requirements
- Windows 10/11 (64-bit)
- ~2GB free disk space (for temp files during processing)
- Internet only needed for YouTube downloads

## Notes
- Temp files stored in `.tmp/` next to executable (auto-cleaned)
- Output files saved to chosen folder (defaults to input file's folder)
- yt-dlp version fixed at build time (no auto-update)

## Support
Report issues at: [repository URL]
```

---

## Antivirus Considerations
- PyInstaller unsigned .exe may trigger Windows SmartScreen
- **Mitigation**: Provide SHA256 checksum in release notes
- **Optional**: Code signing certificate (not included in this workflow)

---

## Version Tracking
- Version defined in `src/__init__.py`: `__version__ = "1.0.0"`
- Embedded in .exe metadata via PyInstaller `--version-file`

---

## Success Criteria
- [ ] Portable folder runs on clean Windows 10/11 VM
- [ ] Source installs and runs via both .bat and .ps1
- [ ] All 3 tools work end-to-end
- [ ] Dracula theme consistent across all widgets
- [ ] Pre-bundled `small.en` model loads without internet
- [ ] Custom icon visible
- [ ] ZIP file < 500MB
- [ ] No console window appears
- [ ] Temp files cleaned after each job