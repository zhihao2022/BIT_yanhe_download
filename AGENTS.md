# AGENTS.md

## Project Overview

This repository is a Python downloader for BIT Yanhe Classroom recordings. It provides command-line, curses-based, and Flask web UI entry points for downloading HLS/M3U8 video streams and optional audio tracks.

## Main Files

- `main.py`: simple command-line entry point.
- `gui.py`: terminal UI entry point using curses.
- `webui_interface.py`: Flask web server entry point.
- `m3u8dl.py`: core M3U8/HLS download, retry, and merge logic.
- `utils.py`: Yanhe API, auth token, signature, and helper functions.
- `gen_caption.py`: optional subtitle generation flow using Whisper.
- `templates/` and `webui/`: browser UI template and static assets.
- `hooks/`: PyInstaller hook files used for packaging.

## Python Environment

- Use `uv` for environment and dependency management.
- The project targets Python `3.14`, as declared in `.python-version` and `pyproject.toml`.
- Create the local virtual environment in the repository root:

```powershell
uv venv
```

- Install the default project dependencies from `pyproject.toml` / `uv.lock`:

```powershell
uv sync
```

- Install optional Whisper dependencies only when subtitle generation is needed:

```powershell
uv sync --extra whisper
```

## Common Commands

```powershell
uv run python main.py
uv run python gui.py
uv run python webui_interface.py
```

The downloader expects `ffmpeg` to be available on `PATH` for media merging.

## Generated and Sensitive Files

- Do not commit `.venv/`, `output/`, build artifacts, release archives, `auth.txt`, model files, or generated JSON files.
- `auth.txt` may contain a user authentication token and must remain local.
- Downloaded media belongs under `output/`.

## Development Notes

- Keep changes scoped to the entry point or module being modified.
- Prefer existing helper functions in `utils.py` and `m3u8dl.py` over duplicating request, signing, retry, or path handling logic.
- Preserve Windows compatibility; the project includes `windows-curses` for Windows terminal UI support.
- If changing web UI behavior, update both `webui_interface.py` and the matching files under `templates/` or `webui/` as needed.

## Version Control

- This project should be managed with a local Git repository.
- After adding or changing project files, run `git add` and create a Git commit.
