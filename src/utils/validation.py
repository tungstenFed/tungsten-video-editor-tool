"""
Input validation utilities
"""
import re
from pathlib import Path
from typing import Tuple, Optional
from .file_dialogs import VIDEO_FILETYPES


def validate_input_video(path_str: str) -> Tuple[bool, str]:
    """Validate input video file path."""
    if not path_str or not path_str.strip():
        return False, "No input file selected"
    
    path = Path(path_str.strip())
    
    if not path.exists():
        return False, f"File not found: {path}"
    
    if not path.is_file():
        return False, f"Not a file: {path}"
    
    # Check extension
    valid_exts = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v", ".mpg", ".mpeg", ".wmv", ".3gp"}
    if path.suffix.lower() not in valid_exts:
        return False, f"Unsupported format: {path.suffix}. Supported: {', '.join(sorted(valid_exts))}"
    
    return True, ""


def validate_output_folder(path_str: str) -> Tuple[bool, str]:
    """Validate output folder path."""
    if not path_str or not path_str.strip():
        return False, "No output folder selected"
    
    path = Path(path_str.strip())
    
    if path.exists() and not path.is_dir():
        return False, f"Path exists but is not a folder: {path}"
    
    # Try to create if doesn't exist
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        return False, f"Cannot create/access folder: {e}"
    
    # Test write permission
    test_file = path / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError):
        return False, f"No write permission in folder: {path}"
    
    return True, ""


def validate_youtube_url(url: str) -> Tuple[bool, str]:
    """Validate YouTube URL."""
    if not url or not url.strip():
        return False, "URL cannot be empty"
    
    url = url.strip()
    
    # YouTube URL patterns
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[\w-]+",
        r"^https?://(www\.)?youtube\.com/embed/[\w-]+",
        r"^https?://youtu\.be/[\w-]+",
        r"^https?://(www\.)?youtube\.com/v/[\w-]+",
        r"^https?://m\.youtube\.com/watch\?v=[\w-]+",
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True, ""
    
    return False, "Invalid YouTube URL format"


def validate_output_filename(name: str) -> Tuple[bool, str]:
    """Validate output filename (without extension)."""
    if not name or not name.strip():
        return False, "Filename cannot be empty"
    
    name = name.strip()
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        if char in name:
            return False, f"Filename cannot contain: {invalid_chars}"
    
    # Check length
    if len(name) > 200:
        return False, "Filename too long (max 200 characters)"
    
    return True, ""


def validate_silence_threshold(value: float) -> Tuple[bool, str]:
    """Validate silence threshold (dB)."""
    if value <= 0:
        return False, "Threshold must be positive"
    if value > 100:
        return False, "Threshold too high (max 100 dB). Typical range: 20-50"
    return True, ""


def validate_buffer(value: float) -> Tuple[bool, str]:
    """Validate buffer seconds."""
    if value < 0:
        return False, "Buffer must be non-negative"
    if value > 60:
        return False, "Buffer too high (max 60 seconds)"
    return True, ""


def validate_min_duration(value: float) -> Tuple[bool, str]:
    """Validate minimum silence duration."""
    if value <= 0:
        return False, "Minimum duration must be positive"
    if value > 60:
        return False, "Minimum duration too high (max 60 seconds)"
    return True, ""


def validate_whisper_model(model: str) -> Tuple[bool, str]:
    """Validate Whisper model name."""
    valid_models = {
        "tiny", "tiny.en", "base", "base.en",
        "small", "small.en", "medium", "medium.en",
        "large-v1", "large-v2", "large-v3",
    }
    if model not in valid_models:
        return False, f"Invalid model. Valid: {', '.join(sorted(valid_models))}"
    return True, ""


def validate_language(lang: str) -> Tuple[bool, str]:
    """Validate language code."""
    if lang == "auto":
        return True, ""
    if not re.match(r"^[a-z]{2}$", lang):
        return False, "Language must be 'auto' or 2-letter code (e.g., 'en', 'es')"
    return True, ""


def validate_max_words(value: int) -> Tuple[bool, str]:
    """Validate max words per subtitle line."""
    if value < 0:
        return False, "Max words must be non-negative"
    if value > 50:
        return False, "Max words too high (max 50)"
    return True, ""