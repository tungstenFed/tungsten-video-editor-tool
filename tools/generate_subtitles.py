
"""
Generate SRT subtitles from an .mp4 video using faster-whisper (local, offline).

Interactive mode — just run and follow prompts:
    python tools/generate_subtitles.py
"""

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()

VALID_MODELS = {"tiny", "tiny.en", "base", "base.en",
                "small", "small.en", "medium", "medium.en",
                "large-v1", "large-v2", "large-v3"}


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


# ──────────────────────────────  Audio / SRT  ────────────────────────────── #

def extract_audio(input_path, output_wav, tmp_dir):
    """Extract 16 kHz mono PCM audio from video for Whisper."""
    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True)

    subprocess.run(
        [
            FFMPEG, "-i", str(input_path),
            "-ar", "16000", "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y", str(output_wav),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        timeout=600,
    )


def format_timestamp(seconds):
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1_000
    millis = total_ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segment_to_srt(idx, start, end, text):
    """Format a single Whisper segment as an SRT block."""
    lines = [str(idx), f"{format_timestamp(start)} --> {format_timestamp(end)}"]
    # Split long text into 2 lines of ~42 chars max (standard SRT convention)
    text = text.strip()
    if len(text) <= 84:
        lines.append(text)
    else:
        half = len(text) // 2
        first = text[:half].rsplit(" ", 1)[0] if " " in text[:half] else text[:half]
        second = text[len(first):].strip() or text[half:]
        lines.append(first)
        lines.append(second)
    lines.append("")
    return "\n".join(lines)


def words_to_chunked_srt(segments, max_words):
    """Build SRT content by grouping words into chunks of up to *max_words*.

    This produces short, frequent subtitle entries that update as the speaker
    talks — each entry spans the first word's start to the last word's end in
    the chunk.
    """
    all_words = []
    for seg in segments:
        if hasattr(seg, "words") and seg.words and hasattr(seg.words[0], "word"):
            all_words.extend(seg.words)
        else:
            # Fall back to single-word entries from segment text
            for word_text in seg.text.strip().split():
                all_words.append(
                    type("W", (), {"word": word_text, "start": seg.start, "end": seg.end})
                )

    srt_parts = []
    idx = 1
    for i in range(0, len(all_words), max_words):
        chunk = all_words[i: i + max_words]
        start = chunk[0].start
        end = chunk[-1].end
        text = " ".join(w.word.strip() for w in chunk)
        srt_parts.append(segment_to_srt(idx, start, end, text))
        idx += 1

    return "\n".join(srt_parts)


def write_srt(srt_content, output_path):
    """Write SRT content with UTF-8 encoding."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)


# ──────────────────────────────  Interactive Prompts  ────────────────────────────── #

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


def main():
    print("=" * 55)
    print("  Subtitle Generator (faster-whisper, offline)")
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
            # Re-prompt if nothing entered
            print("  An input file is required.")

    # ── Output .srt file ──
    default_output = input_path.with_name(f"{input_path.stem}.srt")
    output_path_str = prompt("Output .srt file", default=default_output)
    if output_path_str:
        if not validate_output_file(output_path_str, input_path):
            sys.exit(1)
        output_path = Path(output_path_str)
    else:
        output_path = default_output

    # ── Whisper model ──
    model = prompt(
        "Whisper model",
        default="small.en",
        cast=str,
        validate_fn=lambda m: m in VALID_MODELS,
        error_msg=f"Valid models: {', '.join(sorted(VALID_MODELS))}",
    )

    # ── Language ──
    language = prompt(
        "Language code (e.g. 'en', 'es', 'auto')",
        default="auto",
        cast=str,
        validate_fn=lambda l: l == "auto" or (len(l) == 2 and l.isalpha()),
        error_msg="Enter a 2-letter code (e.g. 'en') or 'auto'.",
    )

    # ── Max words per subtitle ──
    max_words = prompt(
        "Max words per subtitle line (0 = use Whisper segments)",
        default=7,
        cast=int,
        validate_fn=lambda w: w >= 0,
        error_msg="Enter a non-negative integer (e.g. 7 or 0).",
    )

    # ── Get video info ──
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
    if not has_audio:
        print("Error: no audio stream found in the video.")
        sys.exit(1)

    # ── Display configuration ──
    use_word_ts = max_words > 0
    print()
    print("Configuration:")
    print(f"  Input   : {input_path}")
    print(f"  Output  : {output_path}")
    print(f"  Model   : {model}")
    print(f"  Language: {language}" if language != "auto" else "  Language: auto-detect")
    mode = f"chunked (max {max_words} words)" if use_word_ts else "Whisper segments"
    print(f"  Mode    : {mode}")
    if duration:
        print(f"  Duration: {duration:.2f}s")
    print()

    # ── Extract audio ──
    tmp_dir = Path(".tmp")
    audio_path = tmp_dir / "audio_extracted.wav"

    print("Extracting audio ...")
    t0 = time.time()
    try:
        extract_audio(input_path, audio_path, tmp_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e.stderr}")
        sys.exit(1)

    # ── Transcribe ──
    print("Transcribing with faster-whisper ...")
    from faster_whisper import WhisperModel

    transcribe_t0 = time.time()
    model_obj = WhisperModel(
        model,
        device="cpu",
        compute_type="int8",
    )

    language_arg = language if language != "auto" else None

    # VAD filter speeds up inference by skipping silence, but conflicts with
    # word-level timestamps (produces sparse word detection). Disable when
    # using max_words chunking.
    use_vad = not use_word_ts

    segments, info = model_obj.transcribe(
        str(audio_path),
        language=language_arg,
        word_timestamps=use_word_ts,
        vad_filter=use_vad,
    )

    # Materialize segments (faster-whisper returns a generator)
    seg_list = list(segments)
    transcribe_elapsed = time.time() - transcribe_t0

    # ── Write SRT ──
    print("Generating SRT ...")
    if use_word_ts:
        srt_content = words_to_chunked_srt(seg_list, max_words)
    else:
        # Segment-level: each Whisper segment is one SRT entry
        srt_parts = []
        for idx, seg in enumerate(seg_list, 1):
            srt_parts.append(segment_to_srt(idx, seg.start, seg.end, seg.text))
        srt_content = "\n".join(srt_parts)
    write_srt(srt_content, output_path)

    # ── Cleanup ──
    if audio_path.exists():
        audio_path.unlink()

    total_elapsed = time.time() - t0

    # ── Summary ──
    print(f"\n{'=' * 50}")
    print(f"Input         : {input_path}")
    print(f"Output        : {output_path}")
    print(f"Model         : {model}")
    if duration:
        print(f"Video duration: {duration:.2f}s")
    print(f"Segments      : {len(seg_list)}")
    if use_word_ts:
        word_count = sum(
            len(getattr(s, "words", [])) for s in seg_list
            if hasattr(s, "words") and s.words
        )
        print(f"Words         : {word_count}")
        print(f"Max words/line: {max_words}")
    print(f"Transcribe    : {transcribe_elapsed:.1f}s")
    print(f"Total time    : {total_elapsed:.1f}s")


def run_subtitles(input_path: Path, output_path: Path, model: str,
                   language: str, max_words: int, progress_cb=None) -> dict:
    """
    Programmatic entry point for subtitle generation.
    
    Args:
        progress_cb: optional callable(percent:int, message:str) to report
                     intermediate progress back to the caller.

    Returns:
        dict with keys: success, output_path, segments, words, duration,
        transcribe_time, total_time, error
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
    if model not in VALID_MODELS:
        return {"success": False, "error": f"Invalid model: {model}. Valid: {', '.join(sorted(VALID_MODELS))}"}
    if language != "auto" and not (len(language) == 2 and language.isalpha()):
        return {"success": False, "error": "Language must be 'auto' or 2-letter code"}
    if max_words < 0:
        return {"success": False, "error": "Max words must be non-negative"}
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report(5, 'Probe video')
    
    # Get video info
    result = subprocess.run(
        [FFMPEG, "-i", str(input_path)],
        capture_output=True, text=True, timeout=600,
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
    if not has_audio:
        return {"success": False, "error": "No audio stream found in the video"}
    
    # Extract audio
    report(15, 'Extract audio')
    tmp_dir = Path(".tmp")
    audio_path = tmp_dir / "audio_extracted.wav"
    
    try:
        extract_audio(input_path, audio_path, tmp_dir)
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Error extracting audio: {e.stderr}"}
    
    # Transcribe
    from faster_whisper import WhisperModel
    
    transcribe_t0 = time.time()
    report(25, f"Loading model '{model}'...")
    model_obj = WhisperModel(
        model,
        device="cpu",
        compute_type="int8",
    )
    
    language_arg = language if language != "auto" else None
    use_word_ts = max_words > 0
    use_vad = not use_word_ts
    
    report(40, 'Transcribing')
    try:
        segments, info = model_obj.transcribe(
            str(audio_path),
            language=language_arg,
            word_timestamps=use_word_ts,
            vad_filter=use_vad,
        )
    except Exception as e:
        if audio_path.exists():
            audio_path.unlink()
        return {"success": False, "error": f"Transcription failed: {type(e).__name__}: {e}"}
    
    # Materialize segments
    report(80, 'Writing subtitles')
    seg_list = list(segments)
    transcribe_elapsed = time.time() - transcribe_t0
    
    # Write SRT
    report(85, 'Formatting subtitles')
    if use_word_ts:
        srt_content = words_to_chunked_srt(seg_list, max_words)
    else:
        srt_parts = []
        for idx, seg in enumerate(seg_list, 1):
            srt_parts.append(segment_to_srt(idx, seg.start, seg.end, seg.text))
        srt_content = "\n".join(srt_parts)
    
    report(90, 'Saving subtitle file')
    try:
        write_srt(srt_content, output_path)
    except Exception as e:
        if audio_path.exists():
            audio_path.unlink()
        return {"success": False, "error": f"Failed to write SRT: {e}"}
    
    report(95, 'Finalizing')
    # Cleanup
    if audio_path.exists():
        audio_path.unlink()
    
    total_elapsed = time.time() - t0
    
    # Count words if using word timestamps
    word_count = 0
    if use_word_ts:
        word_count = sum(
            len(getattr(s, "words", [])) for s in seg_list
            if hasattr(s, "words") and s.words
        )
    
    report(100, 'Complete')
    
    return {
        "success": True,
        "output_path": str(output_path),
        "segments": len(seg_list),
        "words": word_count,
        "duration": duration,
        "transcribe_time": transcribe_elapsed,
        "total_time": total_elapsed,
        "error": None
    }


if __name__ == "__main__":
    main()
