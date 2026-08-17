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
Report issues at: https://github.com/your-repo/tungsten-video-editor
