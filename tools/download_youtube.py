"""
Download YouTube videos as MP3 using yt-dlp.

Interactive mode — just run and follow prompts:
    python tools/download_youtube.py

Programmatic entry point:
    run_download(url, output_filename, progress_cb=None) -> dict
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yt_dlp


def _atomic_write_progress(job_dir: Path, percent: int, message: str) -> None:
    """Write a progress step file with retry on Windows (atomic replace)."""
    job_dir.mkdir(parents=True, exist_ok=True)
    fname = f"step_{percent:03d}_{int(time.time() * 1000)}.txt"
    path = job_dir / fname
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(f"{percent}\n{message}\n", encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(str(tmp_path), str(path))
            break
        except OSError:
            time.sleep(0.05 * (attempt + 1))
    else:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def make_status_hook(progress_cb, job_dir: Path):
    """Create a yt-dlp status hook that reports progress via callback and file."""
    last_reported_percent = {"value": -1}
    last_reported_time = {"value": 0}

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("_total_bytes") or d.get("total_bytes") or 0
            downloaded = d.get("_downloaded_bytes") or d.get("downloaded_bytes") or 0
            
            if total > 0:
                percent = min(95, int(downloaded / total * 100))
                fraction = downloaded / total
                msg = f"Downloading {d.get('_filename') or '...'} {fraction*100:.1f}% ({_format_bytes(downloaded)}/{_format_bytes(total)})"
            else:
                # Unknown total - show downloaded bytes and don't show percent
                percent = last_reported_percent["value"]
                msg = f"Downloading... {_format_bytes(downloaded)} received"
            
            # Force update at least every 2 seconds or when percent changes
            import time as _time
            now = _time.time()
            if percent != last_reported_percent["value"] or (now - last_reported_time["value"]) > 2.0:
                if progress_cb:
                    progress_cb(percent, msg)
                if job_dir is not None:
                    _atomic_write_progress(job_dir, percent, msg)
                last_reported_percent["value"] = percent
                last_reported_time["value"] = now

        elif d["status"] == "finished":
            percent = 95
            msg = "Download complete, converting to MP3..."
            if progress_cb:
                progress_cb(percent, msg)
            if job_dir is not None:
                _atomic_write_progress(job_dir, percent, msg)
            last_reported_percent["value"] = percent

    return hook


def make_postprocessor_hook(progress_cb, job_dir: Path):
    """Create a yt-dlp postprocessor hook that reports FFmpeg conversion progress."""
    
    def hook(d):
        if d["status"] == "started":
            percent = 95
            msg = f"Converting to MP3: {d.get('postprocessor', 'FFmpegExtractAudio')}"
            if progress_cb:
                progress_cb(percent, msg)
            if job_dir is not None:
                _atomic_write_progress(job_dir, percent, msg)
        
        elif d["status"] == "finished":
            percent = 98
            msg = "MP3 conversion complete"
            if progress_cb:
                progress_cb(percent, msg)
            if job_dir is not None:
                _atomic_write_progress(job_dir, percent, msg)

    return hook


def _format_bytes(num_bytes: float) -> str:
    if num_bytes >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.2f} KB"
    return f"{int(num_bytes)} B"


def _validate_url(url: str) -> tuple[bool, str]:
    """Basic validation that URL looks like a YouTube URL."""
    if not url or not url.strip():
        return False, "URL cannot be empty"
    url = url.strip()
    # Check for common YouTube URL patterns
    valid_prefixes = (
        "https://www.youtube.com/",
        "https://youtu.be/",
        "https://youtube.com/",
        "http://www.youtube.com/",
        "http://youtu.be/",
        "http://youtube.com/",
        "https://m.youtube.com/",
    )
    if not url.startswith(valid_prefixes):
        return False, "URL does not appear to be a valid YouTube URL"
    if "youtube.com" in url and "watch" not in url and "youtu.be" not in url and "embed" not in url and "shorts" not in url:
        # Allow /shorts/, /embed/, /watch, youtu.be — reject others
        pass
    return True, ""


def run_download(url: str, output_filename: str, job_dir: Path = None, progress_cb=None, output_path: Path = None) -> dict[str, Any]:
    """
    Download a single YouTube video as MP3.

    Args:
        url: YouTube video URL
        output_filename: Output filename (without .mp3 extension)
        job_dir: Optional Path to job directory for file-based progress
        progress_cb: optional callable(percent:int, message:str) to report progress
        output_path: Optional full output path (including directory and filename)

    Returns:
        dict with keys: success, output_path, title, duration, error
    """
    def report(percent: int, message: str):
        if progress_cb:
            progress_cb(percent, message)
        if job_dir is not None:
            _atomic_write_progress(job_dir, percent, message)

    t0 = time.time()

    # Validate URL
    is_valid, err_msg = _validate_url(url)
    if not is_valid:
        report(0, f"Invalid URL: {err_msg}")
        return {"success": False, "error": err_msg, "output_path": None, "title": None}

    if not output_filename or not output_filename.strip():
        report(0, "Output filename cannot be empty")
        return {"success": False, "error": "Output filename cannot be empty", "output_path": None, "title": None}

    output_filename = output_filename.strip()

    report(1, f"Processing URL: {url}")

    # Determine output path
    if output_path is not None:
        # Use provided output path
        final_output_path = Path(output_path)
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Fallback to .downloads folder in cwd
        safe_filename = output_filename.replace("/", "_").replace("\\", "_").replace(":", "_")
        output_dir = Path.cwd() / ".downloads"
        output_dir.mkdir(parents=True, exist_ok=True)
        final_output_path = output_dir / f"{safe_filename}.mp3"

    # Remove existing file to avoid yt-dlp conflicts
    if final_output_path.exists():
        try:
            final_output_path.unlink()
        except OSError:
            pass

    report(5, f"Output: {final_output_path.name}")

    # yt-dlp options:
    # - Download single video (no playlist)
    # - Extract audio, convert to MP3
    # - No metadata embedding
    # - Progress via hook
    ydl_opts: dict[str, Any] = {
        # No playlist — single video only
        "noplaylist": True,
        # Extract audio → MP3, prefer formats with known content-length for better progress
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        # No embedded metadata or thumbnail
        "writethumbnail": False,
        "embedthumbnail": False,
        "embedinfojson": False,
        "embedchapters": False,
        "postprocessor_args": ["-metadata", "title=", "-metadata", "artist="],
        # Output template: just the filename we want
        "outtmpl": str(output_path.with_suffix("")),  # without extension, yt-dlp adds _<id>.mp3 → we handle below
        # Progress hooks
        "progress_hooks": [make_status_hook(progress_cb, job_dir)],
        "postprocessor_hooks": [make_postprocessor_hook(progress_cb, job_dir)],
        # Suppress normal output, we capture via hooks + errors
        "quiet": True,
        "no_warnings": False,
        # Network / robustness
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 10,
        # Disable yt-dlp's own progress output (we have our own hook)
        "noprogress": True,
        # Force MP3 extension
        "ffmpeg_args": ["-ar", "44100"],
    }

    # We need the output to be exactly output_path. yt-dlp with postprocessors
    # will name the file <outtmpl>.mp3. So we set outtmpl without extension
    # and expect the MP3 at output_path. But yt-dlp may append video ID if
    # the file already exists or for disambiguation. We'll handle this
    # by using a unique temp folder.

    # Use a temporary working directory to ensure clean output naming
    tmp_download_dir = Path(".tmp") / f"yt_{int(time.time() * 1000)}"
    tmp_download_dir.mkdir(parents=True, exist_ok=True)

    try:
        ydl_opts["outtmpl"] = str(tmp_download_dir / "%(title)s")

        report(10, "Connecting to YouTube...")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first (without downloading) to get title
                info_dict = ydl.extract_info(url, download=False)

            video_title = info_dict.get("title", "Unknown")
            video_duration = info_dict.get("duration")

            report(25, f"Found video: {video_title}")
            report(30, "Starting download...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        except yt_dlp.utils.DownloadError as e:
            error_str = str(e)
            report(0, f"Download error: {error_str}")
            return {
                "success": False,
                "error": error_str,
                "output_path": None,
                "title": video_title if 'video_title' in dir() else None,
            }
        except Exception as e:
            error_str = f"{type(e).__name__}: {e}"
            report(0, f"Error: {error_str}")
            return {
                "success": False,
                "error": error_str,
                "output_path": None,
                "title": video_title if 'video_title' in dir() else None,
            }

        report(90, "Finalizing MP3 file...")

        # Find the downloaded MP3 file (yt-dlp names it <title>.mp3)
        mp3_files = list(tmp_download_dir.glob("*.mp3"))

        if not mp3_files:
            # Check for any .mp3 in output_dir from potential fallback
            report(0, "Error: MP3 file not found after download")
            return {
                "success": False,
                "error": "MP3 file not found after download. The conversion may have failed.",
                "output_path": None,
                "title": video_title if 'video_title' in dir() else None,
            }

        downloaded_mp3 = mp3_files[0]

        # Move the file to the final output path
        # If target exists, remove it first
        if final_output_path.exists():
            final_output_path.unlink()

        shutil.move(str(downloaded_mp3), str(final_output_path))

        report(95, "Done!")

        total_time = time.time() - t0

        return {
            "success": True,
            "output_path": str(final_output_path),
            "title": video_title if 'video_title' in dir() else None,
            "duration": video_duration if 'video_duration' in dir() else None,
            "total_time": total_time,
            "error": None,
        }

    finally:
        # Cleanup temp directory
        if tmp_download_dir.exists():
            shutil.rmtree(tmp_download_dir, ignore_errors=True)


def main():
    """Interactive mode for testing."""
    print("=" * 55)
    print("  YouTube to MP3 Downloader")
    print("=" * 55)
    print()

    url = input("YouTube URL: ").strip()

    is_valid, err = _validate_url(url)
    if not is_valid:
        print(f"Error: {err}")
        sys.exit(1)

    filename = input("Output filename (without .mp3): ").strip()
    if not filename:
        print("Error: filename is required")
        sys.exit(1)

    def progress(percent, msg):
        print(f"[{percent}%] {msg}")

    result = run_download(url, filename, progress_cb=progress)

    if result["success"]:
        print(f"\nDone! Saved to: {result['output_path']}")
        print(f"Title: {result['title']}")
        if result.get("duration"):
            print(f"Duration: {result['duration']}s")
    else:
        print(f"\nFailed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
