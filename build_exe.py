#!/usr/bin/env python3
"""
PyInstaller build script for Tungsten Video Editor
Creates a portable folder distribution with pre-bundled whisper model
"""
import sys
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
PORTABLE = ROOT / "TungstenVideoEditor-Portable"
ASSETS = ROOT / "assets"


def clean_previous_builds():
    """Remove previous build artifacts."""
    for path in [DIST, BUILD, PORTABLE]:
        if path.exists():
            print(f"Cleaning {path}...")
            shutil.rmtree(path, ignore_errors=True)


def ensure_whisper_model():
    """Pre-download the small.en whisper model for bundling."""
    print("Checking/downloading whisper small.en model...")
    try:
        # This will download the model to the cache if not present
        from faster_whisper import WhisperModel
        model = WhisperModel("small.en", device="cpu", compute_type="int8")
        print("Model ready")
        return True
    except Exception as e:
        print(f"Warning: Could not pre-download model: {e}")
        return False


def get_model_cache_path():
    """Get the path to the cached whisper model."""
    import os
    cache_dir = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    model_dir = cache_dir / "hub" / "models--Systran--faster-whisper-small.en"
    return model_dir if model_dir.exists() else None


def build_exe():
    """Run PyInstaller to build the application."""
    model_cache = get_model_cache_path()
    
    # Base PyInstaller arguments
    args = [
        "main.py",
        "--name=TungstenVideoEditor",
        "--onedir",                    # Portable folder output
        "--windowed",                  # No console window
        "--clean",                     # Clean cache before building
        f"--distpath={DIST}",
        f"--workpath={BUILD}",
        # Data files
        "--add-data=tools;tools",
        "--add-data=src;src",
    ]
    
    # Add icon if exists
    icon_path = ASSETS / "icon.ico"
    if icon_path.exists():
        args.append(f"--icon={icon_path}")
    
    # Add whisper model if available
    if model_cache and model_cache.exists():
        args.append(f"--add-data={model_cache};systran/faster-whisper-small.en")
        print(f"Bundling whisper model from: {model_cache}")
    else:
        print("Warning: Whisper model not found in cache, will download on first run")
    
    # Hidden imports
    hidden_imports = [
        "faster_whisper",
        "yt_dlp",
        "ffmpeg",
        "imageio_ffmpeg",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
        "tkinter.ttk",
        "ctypes",
        "ctypes.wintypes",
    ]
    for imp in hidden_imports:
        args.append(f"--hidden-import={imp}")
    
    # Collect all submodules
    args.extend([
        "--collect-all=faster_whisper",
        "--collect-all=yt_dlp",
        "--collect-submodules=faster_whisper",
    ])
    
    print("Running PyInstaller...")
    print(f"Command: pyinstaller {' '.join(args)}")
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller"] + args,
        capture_output=False,
        text=True,
    )
    
    if result.returncode != 0:
        print("PyInstaller failed!")
        return False
    
    return True


def create_portable_folder():
    """Create the final portable folder structure."""
    source = DIST / "TungstenVideoEditor"
    if not source.exists():
        print(f"Build output not found at {source}")
        return False
    
    print(f"Creating portable folder at {PORTABLE}...")
    shutil.copytree(source, PORTABLE)
    
    # Create README
    readme = PORTABLE / "README.md"
    readme.write_text(PORTABLE_README)
    
    print("Portable folder created successfully!")
    return True


def verify_build():
    """Verify the portable build works."""
    exe_path = PORTABLE / "TungstenVideoEditor.exe"
    if not exe_path.exists():
        print(f"ERROR: Executable not found at {exe_path}")
        return False
    
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"Executable size: {size_mb:.1f} MB")
    
    # Check total folder size
    total_size = sum(f.stat().st_size for f in PORTABLE.rglob("*") if f.is_file())
    total_mb = total_size / (1024 * 1024)
    print(f"Total portable folder size: {total_mb:.1f} MB")
    
    if total_mb > 500:
        print(f"WARNING: Folder size ({total_mb:.1f} MB) exceeds 500 MB target")
    
    return True


PORTABLE_README = """# Tungsten Video Editor - Portable Edition

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


"""


def main():
    """Main build process."""
    print("=" * 60)
    print("Tungsten Video Editor - Build Script")
    print("=" * 60)
    
    # Step 1: Clean
    clean_previous_builds()
    
    # Step 2: Ensure whisper model
    ensure_whisper_model()
    
    # Step 3: Build
    if not build_exe():
        print("BUILD FAILED")
        sys.exit(1)
    
    # Step 4: Create portable folder
    if not create_portable_folder():
        print("FAILED TO CREATE PORTABLE FOLDER")
        sys.exit(1)
    
    # Step 5: Verify
    if not verify_build():
        print("BUILD VERIFICATION FAILED")
        sys.exit(1)
    
    print("=" * 60)
    print("BUILD SUCCESSFUL!")
    print(f"Portable folder: {PORTABLE}")
    print("=" * 60)


if __name__ == "__main__":
    main()