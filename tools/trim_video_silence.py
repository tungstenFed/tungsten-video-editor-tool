
"""
Auto-trim audio silence from .mp4 videos.

Interactive mode — just run and follow prompts:
    python tools/trim_video_silence.py
"""

import re
import subprocess
import sys
import time
import os
from pathlib import Path
from typing import Optional

import ffmpeg as ffmpeg_python
from imageio_ffmpeg import get_ffmpeg_exe

if not hasattr(ffmpeg_python, "input"):
    raise ImportError(
        "ffmpeg-python package appears corrupted (empty __init__.py). "
        "Fix: pip install --force-reinstall ffmpeg-python"
    )

FFMPEG = get_ffmpeg_exe()


# ──────────────────────────────  Helpers  ────────────────────────────── #

def prompt(msg, default=None, cast=None, validate_fn=None, error_msg="Invalid input."):
    """Prompt the user for input. Press Enter to accept the default."""
    hint = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{msg}{hint}: ").strip()
        if not raw:
            return default
        try:
            val = cast(raw) if cast else raw
        except (ValueError, TypeError):
            print(f"  {error_msg}")
            continue
        if validate_fn and not validate_fn(val):
            print(f"  {error_msg}")
            continue
        return val


def validate_input_file(path_str):
    p = Path(path_str)
    if not p.exists():
        print(f"  File not found: {p}")
        return False
    if p.suffix.lower() != ".mp4":
        print(f"  Input must be .mp4 (got '{p.suffix}').")
        return False
    return True


def validate_output_file(path_str, input_path):
    p = Path(path_str)
    if p.resolve() == input_path.resolve():
        print("  Output path must differ from input.")
        return False
    return True


def get_video_info(input_path):
    """Return (duration_seconds, has_audio) by probing with ffmpeg -i."""
    result = subprocess.run(
        [FFMPEG, "-i", str(input_path)],
        capture_output=True, text=True
    )
    stderr = result.stderr

    duration = None
    m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", stderr)
    if m:
        duration = (
            float(m.group(1)) * 3600
            + float(m.group(2)) * 60
            + float(m.group(3))
        )

    has_audio = bool(re.search(r"Stream.*Audio", stderr))
    return duration, has_audio


def detect_silence(input_path, threshold, min_duration, progress_cb=None):
    """
    Run ffmpeg's ``silencedetect`` filter and parse stderr.
    Returns two lists: silence_starts, silence_ends.
    
    Args:
        progress_cb: optional callable(percent:int, message:str) for real-time progress
    """
    def report(p, msg):
        if progress_cb:
            progress_cb(p, msg)
    
    report(10, 'Detecting silence...')
    
    # Build ffmpeg command with silencedetect filter
    # noise=-30dB means silence is anything BELOW -30dB
    # d=0.5 means silence must last at least 0.5 seconds
    af_filter = f"silencedetect=noise=-{threshold}dB:d={min_duration}"
    
    proc = subprocess.Popen(
        [
            FFMPEG, "-i", str(input_path),
            "-af", af_filter,
            "-f", "null", "-",
        ],
        stdout=subprocess.DEVNULL,  # Don't capture stdout - can cause deadlock
        stderr=subprocess.PIPE,
        text=True,
    )
    
    starts = []
    ends = []
    last_report = 10
    all_stderr = []
    
    # Read stderr line by line for real-time progress
    for line in proc.stderr:
        line = line.strip()
        all_stderr.append(line)
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([\d.]+)", line)
            if m:
                starts.append(float(m.group(1)))
        elif "silence_end:" in line:
            m = re.search(r"silence_end:\s*([\d.]+)", line)
            if m:
                ends.append(float(m.group(1)))
        elif "time=" in line:
            # Parse ffmpeg progress time
            m = re.search(r"time=(\d+):(\d+):(\d+\.?\d*)", line)
            if m:
                h, m, s = m.groups()
                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                # We don't know total duration here, but we can report activity
                report(min(50, last_report + 1), f'Analyzing... {int(current_time)}s')
    
    proc.wait(timeout=3600)
    if proc.returncode != 0:
        stdout, stderr = proc.communicate()
        raise subprocess.CalledProcessError(proc.returncode, proc.args, stdout, stderr)
    
    # Debug: log what was detected
    debug_msg = f"Silence detection complete: {len(starts)} starts, {len(ends)} ends (threshold=-{threshold}dB, min_dur={min_duration}s)"
    if starts:
        debug_msg += f" | starts: {[f'{s:.2f}' for s in starts[:5]]}"
    if ends:
        debug_msg += f" | ends: {[f'{e:.2f}' for e in ends[:5]]}"
    report(50, debug_msg)
    
    return starts, ends


def pair_silence(starts, ends, duration):
    """Pair every silence_start with its silence_end.

    If the last ``silence_start`` has no matching ``silence_end`` (audio
    ended while still silent), pair it with *duration*.
    """
    segments = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration
        segments.append((s, e))
    return segments


def compute_keep_segments(silence_segments, duration, buffer):
    """
    From silence segments, compute the list of time ranges to *keep*.

    Each keep segment extends into the following silence by *buffer* seconds.
    The buffer acts as a tiny breathing-gap that is retained before the
    silence is removed.
    """
    keep = []
    prev_end = 0.0

    for s_start, s_end in silence_segments:
        seg_end = min(s_start + buffer, s_end)
        if prev_end < seg_end:
            keep.append((prev_end, seg_end))
        prev_end = s_end

    # Trailing segment (from last silence end to video end)
    if prev_end < duration:
        keep.append((prev_end, duration))

    return keep


def stream_copy(input_path, output_path):
    """Fast stream-copy (no re-encode) to output."""
    subprocess.run(
        [FFMPEG, "-i", str(input_path), "-c", "copy", "-y", str(output_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        timeout=3600,
    )


def trim_with_ffmpeg_python(input_path, output_path, segments, duration, progress_cb=None):
    """Construct and run the ffmpeg filter graph via ffmpeg-python.
    
    Args:
        progress_cb: optional callable(percent:int, message:str) for progress
    
    Splits the input video/audio into one copy per keep segment, applies
    ``trim`` / ``atrim`` to each, then stitches everything together with
    the ``concat`` filter.
    """
    def report(p, msg):
        if progress_cb:
            progress_cb(p, msg)
    
    if len(segments) == 0:
        stream_copy(input_path, output_path)
        return

    n = len(segments)
    in_node = ffmpeg_python.input(str(input_path))

    # Split into N copies so each segment can consume its own branch.
    # Without this, ffmpeg-python raises "multiple outgoing edges … a
    # split filter is probably required".
    v_split = in_node.video.filter_multi_output("split", **{"outputs": n})
    a_split = in_node.audio.filter_multi_output("asplit", **{"outputs": n})

    concat_inputs = []
    for i, (start, end) in enumerate(segments):
        v = (
            v_split[i]
            .filter("trim", start=start, end=end)
            .filter("setpts", "PTS-STARTPTS")
        )
        a = (
            a_split[i]
            .filter("atrim", start=start, end=end)
            .filter("asetpts", "PTS-STARTPTS")
        )
        concat_inputs.extend([v, a])

    concat = ffmpeg_python.concat(*concat_inputs, v=1, a=1)
    
    # Use subprocess directly with progress reporting
    cmd = (
        concat
        .output(
            str(output_path),
            vcodec="libx264",
            crf=23,
            acodec="aac",
            audio_bitrate=128000,
            movflags="+faststart",
        )
        .compile(cmd=FFMPEG)
    )
    
    report(85, 'Starting video encoding...')
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,  # Don't capture stdout - can cause deadlock
        stderr=subprocess.PIPE,
        text=True,
    )
    
    last_progress = 85
    for line in proc.stderr:
        line = line.strip()
        if "time=" in line:
            m = re.search(r"time=(\d+):(\d+):(\d+\.?\d*)", line)
            if m:
                h, m, s = m.groups()
                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                # Map to 85-99% range based on video duration
                p = min(99, 85 + int(current_time * 14 / max(1, duration)))
                if p > last_progress:
                    report(p, f'Encoding... {int(current_time)}s')
                    last_progress = p
    
    proc.wait(timeout=3600)
    if proc.returncode != 0:
        # Read remaining stderr for error details
        remaining_stderr = proc.stderr.read() if proc.stderr else ""
        raise subprocess.CalledProcessError(proc.returncode, proc.args, "", remaining_stderr)
    
    # Verify output file exists and has content
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise Exception(f"Output file not created or empty: {output_path}")
    
    report(100, 'Complete')


def main():
    print("=" * 55)
    print("  Video Auto-Trimmer (silence removal)")
    print("=" * 55)
    print()

    # ── Input .mp4 file ──
    input_path = None
    while True:
        input_path_str = prompt("Input .mp4 file", default=None)
        if input_path_str:
            p = Path(input_path_str)
            if validate_input_file(input_path_str):
                input_path = p
                break
        else:
            print("  An input file is required.")

    # ── Output .mp4 file ──
    default_output = input_path.with_name(f"{input_path.stem}_trimmed.mp4")
    output_path_str = prompt("Output .mp4 file", default=default_output)
    if output_path_str:
        if not validate_output_file(output_path_str, input_path):
            sys.exit(1)
        output_path = Path(output_path_str)
    else:
        output_path = default_output

    # ── Threshold (required) ──
    threshold = prompt(
        "Silence threshold in dB (e.g. 30 = -30dB)",
        default=None,
        cast=float,
        validate_fn=lambda t: t > 0,
        error_msg="Enter a positive number (e.g. 30, 35, 40).",
    )

    # ── Buffer ──
    buffer = prompt(
        "Buffer seconds to retain at each silence start",
        default=0.0,
        cast=float,
        validate_fn=lambda b: b >= 0,
        error_msg="Enter a non-negative number (e.g. 0.0, 0.1, 0.5).",
    )

    # ── Min duration ──
    min_duration = prompt(
        "Minimum silence duration to qualify (seconds)",
        default=0.5,
        cast=float,
        validate_fn=lambda d: d > 0,
        error_msg="Enter a positive number (e.g. 0.5, 1.0).",
    )

    # ── Validate (already done in prompts) ──
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Get video info ──
    duration, has_audio = get_video_info(input_path)
    if duration is None:
        print("Error: could not determine video duration.")
        sys.exit(1)

    # ── Display configuration ──
    print()
    print("Configuration:")
    print(f"  Input     : {input_path}")
    print(f"  Output    : {output_path}")
    print(f"  Threshold : -{threshold}dB")
    print(f"  Buffer    : {buffer}s")
    print(f"  Min silence: {min_duration}s")
    print(f"  Duration  : {duration:.2f}s")
    print()

    if not has_audio:
        print("Warning: no audio stream found — copying video as-is.")
        stream_copy(input_path, output_path)
        print(f"Output: {output_path}")
        return

    # ── Detect silence ──
    t0 = time.time()
    starts, ends = detect_silence(input_path, threshold, min_duration)

    silence_segments = pair_silence(starts, ends, duration)

    if not silence_segments:
        print("No silence detected — copying video as-is.")
        stream_copy(input_path, output_path)
        elapsed = time.time() - t0
        print(f"\nDone in {elapsed:.1f}s")
        print(f"Output: {output_path}")
        return

    # ── Compute keep segments ──
    keep = compute_keep_segments(silence_segments, duration, buffer)

    if not keep:
        print("Warning: all segments were filtered out (video is mostly silence).")
        print("Copying video as-is.")
        stream_copy(input_path, output_path)
        elapsed = time.time() - t0
        print(f"\nDone in {elapsed:.1f}s")
        print(f"Output: {output_path}")
        return

    # ── Trim ──
    print(f"Silence segments: {len(silence_segments)}")
    print(f"Keep segments   : {len(keep)}")
    print("Trimming ...")

    try:
        trim_with_ffmpeg_python(input_path, output_path, keep, duration)
    except ffmpeg_python.Error as e:
        print("\nError during processing:")
        if e.stderr:
            print(e.stderr.decode(errors="replace"))
        else:
            print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}: {e}")
        sys.exit(1)

    elapsed = time.time() - t0
    trimmed_duration = sum(e - s for s, e in keep)

    # ── Summary ──
    print(f"\n{'=' * 50}")
    print(f"Original duration : {duration:.2f}s")
    print(f"Trimmed duration  : {trimmed_duration:.2f}s")
    print(f"Time removed      : {duration - trimmed_duration:.2f}s "
          f"({(duration - trimmed_duration) / duration * 100:.1f}%)")
    print(f"Silence segments  : {len(silence_segments)}")
    print(f"Buffer per cut    : {buffer}s")
    print(f"Processing time   : {elapsed:.1f}s")
    print(f"Output            : {output_path}")


def run_trim(input_path: Path, output_path: Path, threshold: float,
             buffer: float, min_duration: float,
             progress_cb=None) -> dict:
    """
    Programmatic entry point for silence trimming.
    
    Args:
        progress_cb: optional callable(percent:int, message:str) to report
                     intermediate progress back to the caller.

    Returns:
        dict with keys: success, output_path, original_duration, trimmed_duration,
        silence_segments, processing_time, error
    """
    def report(p, msg):
        if progress_cb:
            progress_cb(p, msg)
    t0 = time.time()
    
    # Validate inputs
    report(1, 'Validate input')
    if not input_path.exists():
        return {"success": False, "error": f"Input file not found: {input_path}"}
    if input_path.suffix.lower() != ".mp4":
        return {"success": False, "error": f"Input must be .mp4 (got '{input_path.suffix}')"}
    if output_path.resolve() == input_path.resolve():
        return {"success": False, "error": "Output path must differ from input"}
    if threshold <= 0:
        return {"success": False, "error": "Threshold must be positive"}
    if threshold > 100:
        return {"success": False, "error": f"Threshold too high: {threshold}. Use 1-100 (lower = more aggressive). Example: 30 = -30dB"}
    if buffer < 0:
        return {"success": False, "error": "Buffer must be non-negative"}
    if min_duration <= 0:
        return {"success": False, "error": "Min duration must be positive"}
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report(5, 'Probe video')
    
    # Get video info
    duration, has_audio = get_video_info(input_path)
    if duration is None:
        return {"success": False, "error": "Could not determine video duration"}
    
    report(10, 'Detect silence')
    
    if not has_audio:
        report(50, 'Fast stream copy (no audio)')
        stream_copy(input_path, output_path)
        return {
            "success": True,
            "output_path": str(output_path),
            "original_duration": duration,
            "trimmed_duration": duration,
            "silence_segments": 0,
            "processing_time": time.time() - t0,
            "error": None
        }
    
    # Detect silence
    starts, ends = detect_silence(input_path, threshold, min_duration, progress_cb=report)
    report(60, 'Compute keep segments')
    silence_segments = pair_silence(starts, ends, duration)
    
    if not silence_segments:
        report(80, 'Fast stream copy (no silence detected)')
        stream_copy(input_path, output_path)
        elapsed = time.time() - t0
        return {
            "success": True,
            "output_path": str(output_path),
            "original_duration": duration,
            "trimmed_duration": duration,
            "silence_segments": 0,
            "processing_time": elapsed,
            "error": f"No silence detected with threshold=-{threshold}dB, min_dur={min_duration}s. Try lower threshold (e.g., 20-30) or shorter min_dur."
        }
    
    # Compute keep segments
    report(70, 'Compute keep segments')
    keep = compute_keep_segments(silence_segments, duration, buffer)
    
    if not keep:
        report(90, 'Fast stream copy')
        stream_copy(input_path, output_path)
        elapsed = time.time() - t0
        return {
            "success": True,
            "output_path": str(output_path),
            "original_duration": duration,
            "trimmed_duration": duration,
            "silence_segments": len(silence_segments),
            "processing_time": elapsed,
            "error": "All segments filtered out (video is mostly silence)"
        }
    
    # Trim
    report(80, 'Re-encode trimmed segments')
    try:
        trim_with_ffmpeg_python(input_path, output_path, keep, duration)
    except ffmpeg_python.Error as e:
        err_msg = e.stderr.decode(errors="replace") if e.stderr else str(e)
        return {"success": False, "error": f"FFmpeg error: {err_msg}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {type(e).__name__}: {e}"}
    
    elapsed = time.time() - t0
    report(100, 'Complete')
    trimmed_duration = sum(e - s for s, e in keep)
    
    return {
        "success": True,
        "output_path": str(output_path),
        "original_duration": duration,
        "trimmed_duration": trimmed_duration,
        "silence_segments": len(silence_segments),
        "processing_time": elapsed,
        "error": None
    }


if __name__ == "__main__":
    main()
