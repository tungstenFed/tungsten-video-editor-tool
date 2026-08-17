"""
FFmpeg format conversion utility
"""
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()

SUPPORTED_INPUT_FORMATS = {
    ".mov", ".mkv", ".avi", ".webm", ".flv", 
    ".m4v", ".mpg", ".mpeg", ".wmv", ".3gp",
    ".mts", ".m2ts", ".ts", ".vob", ".ogv"
}

DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_CRF = 23
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "128k"


def convert_to_mp4(
    input_path: Path,
    output_path: Path,
    progress_cb: Callable[[int, str], None] = None,
    video_codec: str = DEFAULT_VIDEO_CODEC,
    crf: int = DEFAULT_CRF,
    audio_codec: str = DEFAULT_AUDIO_CODEC,
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE,
) -> Path:
    """
    Convert video to MP4 using ffmpeg.
    
    Args:
        input_path: Source video file
        output_path: Destination .mp4 file
        progress_cb: Callback(percent, message) for progress updates
        video_codec: Video codec (default: libx264)
        crf: Constant Rate Factor 0-51 (default: 23)
        audio_codec: Audio codec (default: aac)
        audio_bitrate: Audio bitrate (default: 128k)
    
    Returns:
        Path to converted file
    """
    def report(p: int, msg: str):
        if progress_cb:
            progress_cb(p, msg)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    
    if input_path.suffix.lower() == ".mp4":
        # Already MP4, just copy
        import shutil
        report(10, "Already MP4, copying...")
        shutil.copy2(input_path, output_path)
        report(100, "Done")
        return output_path
    
    report(5, f"Converting {input_path.name} to MP4...")
    
    # Get duration for progress estimation
    duration = _get_duration(input_path)
    
    cmd = [
        FFMPEG,
        "-y",  # Overwrite output
        "-i", str(input_path),
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", "medium",
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-movflags", "+faststart",
        str(output_path),
    ]
    
    report(10, "Starting conversion...")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    
    last_progress = 10
    start_time = time.time()
    
    for line in proc.stderr:
        line = line.strip()
        if "time=" in line and duration:
            # Parse ffmpeg time output
            import re
            m = re.search(r"time=(\d+):(\d+):(\d+\.?\d*)", line)
            if m:
                h, m_, s = m.groups()
                current = int(h) * 3600 + int(m_) * 60 + float(s)
                percent = min(95, 10 + int(current * 85 / duration))
                if percent > last_progress:
                    report(percent, f"Converting... {current:.0f}s / {duration:.0f}s")
                    last_progress = percent
        elif "speed=" in line:
            # Log speed occasionally
            pass
    
    proc.wait(timeout=3600)
    
    if proc.returncode != 0:
        stderr = proc.stderr.read() if proc.stderr else ""
        raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=stderr)
    
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Conversion produced empty file")
    
    report(100, f"Converted to {output_path.name}")
    return output_path


def _get_duration(input_path: Path) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [FFMPEG, "-i", str(input_path)],
            capture_output=True, text=True, timeout=30
        )
        stderr = result.stderr
        import re
        m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return None


def is_supported_format(path: Path) -> bool:
    """Check if file format is supported for conversion."""
    return path.suffix.lower() in SUPPORTED_INPUT_FORMATS or path.suffix.lower() == ".mp4"


def needs_conversion(path: Path) -> bool:
    """Check if file needs conversion to MP4."""
    return path.suffix.lower() != ".mp4" and is_supported_format(path)


def get_temp_converted_path(input_path: Path, tmp_dir: Path) -> Path:
    """Generate temporary converted file path."""
    import time
    timestamp = int(time.time() * 1000)
    return tmp_dir / f"converted_{timestamp}_{input_path.stem}.mp4"