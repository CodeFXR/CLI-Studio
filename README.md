# CLI-Studio

A terminal user interface for image, video, audio, and cloud media manipulation.

CLI-Studio wraps 13 command-line media tools behind one menu-driven Textual TUI:
**ffmpeg**, **yt-dlp**, **Pillow**, **ImageMagick**, **ExifTool**,
**tesseract**, **mkvtoolnix**, **HandBrakeCLI**, **gallery-dl**,
**ffmpeg-normalize**, **rclone**, **zbarimg**, and **chafa**.
[faster-whisper] and [realesrgan-ncnn-vulkan] are optional backends for AI
subtitles and image upscaling respectively.

62 user-facing tools across 5 top-level tabs (Video, Audio, Image, Cloud Tools,
Device Presets) plus a Settings menu and a user-plugin slot. Linux and macOS.

[faster-whisper]: https://github.com/SYSTRAN/faster-whisper
[realesrgan-ncnn-vulkan]: https://github.com/xinntao/Real-ESRGAN

---

## What it does

- **74 tools in a menu-driven wizard.** Every tool is a short chain of modal
  screens (file picker → optional parameter → save picker → progress) that
  gather input then run a subprocess in a worker thread. The TUI stays
  responsive while ffmpeg/yt-dlp/etc. work.
- **Batch by default.** Select a folder instead of a file and cli-studio
  iterates over every matching file with a per-batch progress bar. Per-file
  failures are logged and reported; the batch does not abort.
- **Inline help (`?`).** Every tool has a plain-English description in the
  `HELP_REGISTRY`. Press `?` from any menu to read what a tool does.
- **Atomic config writes.** `~/.cli_studio_config.json` is written via
  `tempfile.mkstemp()` + `os.replace()`. A crash mid-write cannot corrupt it.
- **User-extensible.** Drop a `PLUGIN_REGISTRY = {...}` into any `.py` file in
  `~/.cli-studio/plugins/`. Built-in commands cannot be overwritten.

## What it does not do

- **No GUI.** This is a terminal app. There is no Electron, no web view, no
  thumbnail pane beyond what `chafa` can render in the terminal.
- **No cloud sync, no telemetry.** The app does not phone home. yt-dlp and
  gallery-dl make outbound requests to the URLs you give them — and only those.
- **No background daemon.** Single-process, single-window.
- **No sandbox.** CLI tools run with your user privileges. Plugins run with
  your user privileges. Don't put untrusted code in `~/.cli-studio/plugins/`.

---

## Installation

The installer is a plain bash script (~210 lines). Read it before you run it:

```
https://github.com/codefxr/cli-studio/blob/main/install
```

To install on Linux or macOS:

```bash
curl -fsSL https://cso.codefxr.com/install | bash
```

The script:

1. Installs system packages via your package manager (`apt`, `dnf`,
   `pacman`, or `brew`).
2. Clones the repo into `~/.local/share/cli-studio/`.
3. Creates an isolated Python virtual environment.
4. Installs the Python dependencies (textual, Pillow, yt-dlp, natsort,
   textual-image).
5. Best-effort installs optional Python deps (`ffmpeg-normalize`,
   `gallery-dl`).
6. Creates `cli-studio` and `cso` symlinks in `~/.local/bin/`.
7. If `~/.local/bin` isn't on your `PATH`, **prints the line it would
   append** to your shell RC file and asks `y/N` before writing.

Then run:

```bash
cli-studio
# or
cso
```

To upgrade the Python dependencies later (system packages are not touched):

```bash
cli-studio update
```

### System packages installed

| Tool | apt | dnf | pacman | brew |
|---|---|---|---|---|
| ffmpeg | `ffmpeg` | `ffmpeg` | `ffmpeg` | `ffmpeg` |
| ImageMagick | `imagemagick` | `ImageMagick` | `imagemagick` | `imagemagick` |
| ExifTool | `libimage-exiftool-perl` | `perl-Image-ExifTool` | `perl-image-exiftool` | `exiftool` |
| tesseract | `tesseract-ocr tesseract-ocr-eng` | `tesseract` | `tesseract` | `tesseract` |
| mkvtoolnix | `mkvtoolnix` | `mkvtoolnix` | `mkvtoolnix` | `mkvtoolnix` |
| zbar | `zbar-tools` | `zbar` | `zbar` | `zbar` |
| rename | `rename` | `perl-File-Rename` | `perl-rename` | `rename` |
| rclone | `rclone` | `rclone` | `rclone` | `rclone` |
| HandBrake CLI | `handbrake-cli` | `HandBrake-cli` | `handbrake-cli` | `handbrake` |
| chafa | `chafa` | `chafa` | `chafa` | `chafa` |

`node` is **not** installed automatically. yt-dlp's `--js-runtimes node`
relies on it for sites that require EJS challenge solving; install via your
package manager if you need those sites.

---

## Keyboard shortcuts

| Shortcut | Action |
| :--- | :--- |
| `?` | Help — open the description for the highlighted tool |
| `Ctrl` + `l` | Toggle the raw-execution log console |
| `Alt` + `m` | Open the tools menu |
| `Alt` + `t` | Open the theme picker |
| `Alt` + `s` | Open the settings menu |
| `Alt` + `a` | Open the About panel |
| `Alt` + `b` | Back to the previous menu |
| `Alt` + `e` | Exit |
| `Esc` | Close the current modal or return to the home screen |
| `Ctrl` + `c` | Quit |

Slash commands in the input bar (these are equivalent to the menu shortcuts):

```
/home     /menu     /about     /themes     /settings     /exit
/video    /audio    /image     /cloud         /devices     /back
/themes <name>   apply a theme immediately (e.g. /themes navy)
```

---

## Settings

Open with `Alt+S` or `/settings`. Settings are persisted in
`~/.cli_studio_config.json` (atomic writes, see above).

| Setting | Default | Effect |
|---|---|---|
| `yt_dlp_cookies` | (empty) | Browser profile to read cookies from. **Empty = off.** Set to `chrome`, `firefox`, etc. to enable. |
| `yt_dlp_remote_components` | (empty) | `--remote-components` value. **Empty = off.** |
| `hw_accel` | (empty) | Hardware encoder: `nvenc`, `vaapi`, `videotoolbox`, `qsv`. Empty = software (`libx264`, `libx265`, etc.). |
| `ffmpeg_overwrite` | `On` | When off, ffmpeg passes `-n` (refuse to overwrite). |
| `whisper_model` | `small` | `tiny` / `base` / `small` / `medium` / `large-v3`. |
| `whisper_device` | `auto` | `auto` / `cpu` / `cuda`. |
| `whisper_compute` | `auto` | `auto` / `int8` / `float16` / `float32`. |
| `whisper_cache_dir` | `~/.cache/cli-studio/whisper` | Where faster-whisper stores downloaded models. Must be under `$HOME`, `/tmp`, or `/var/tmp`. |

The cookie and remote-components settings are **off by default** for
privacy. See `SECURITY.md` for the threat model.

---

## Tools at a glance

### Video (`ffmpeg`, `yt-dlp`, `mkvtoolnix`)

`Download Video` · `Download Playlist` · `Download Gallery` · `Convert Video` ·
`Convert Video Preset` · `Trim Video` · `Extract Audio` · `Mute Video` ·
`Change Video Speed` · `Rotate Video` · `Reverse Video` · `Create GIF` ·
`Extract Frames` · `Add Watermark` · `Add Audio Track` · `Scale/Resize Video` ·
`Fade In Video` · `Extract Subtitles` · `Generate Whisper Subtitles` ·
`Burn Subtitles` · `Silence Removal` · `Audio Visualizer` · `Remux Video to MKV` ·
`Merge MKVs` · `Extract MKV Subs` · `Add Subs to MKV` · `Extract MKV Attachments`

### Audio (`ffmpeg`, `ffmpeg-normalize`)

`Download Audio` · `Convert Audio` · `Trim Audio` · `Change Volume` ·
`Change Audio Speed` · `Reverse Audio` · `Normalize Audio` ·
`Normalize Audio (2-pass)` · `Fade In Audio` · `Mix Audio Tracks` ·
`Preview Audio Waveform`

### Image (`Pillow`, `ImageMagick`, `ExifTool`, `tesseract`, `zbarimg`,
`realesrgan-ncnn-vulkan`, `chafa`)

`Convert Image` · `Resize Image` · `Crop Image` · `Rotate Image` · `Flip Image` ·
`Remove Background Color` · `Apply Filter` · `Strip Metadata` ·
`Add Text Watermark` · `Optimize/Compress` · `Convert to PDF` · `Add Border` ·
`Extract Text from Image` · `Preview Image` · `Upscale Image` · `Sprite Sheet` ·
`Set EXIF Tag` · `Copy EXIF` · `Rename by EXIF Date` · `Scan Barcode`

### Cloud Tools (`rclone`)

`Rclone Copy` · `Rclone List Remotes`

### Device Presets (`HandBrakeCLI`)

`Transcode Device Preset` (16 device profiles: Apple, Android, Chromecast, Fire
TV, Roku, Fast, HQ, Super HQ, Vimeo, etc.) · `List HandBrake Presets`

---

## Plugins

Drop a Python file into `~/.cli-studio/plugins/` with this shape:

```python
PLUGIN_REGISTRY = {
    "my tool name": lambda: None,  # builder that returns a ModalScreen
}
PLUGIN_MENU = "video"              # optional: which tab to add it to
PLUGIN_HELP = {                    # optional: help text per tool
    "my tool name": "Plain-English description.",
}
```

Built-in commands win collisions (your plugin's "convert video" is silently
ignored). Valid plugin tools appear in a Plugins menu after the next launch.
Failing or syntax-error plugins are skipped without crashing startup.

---

## Architecture, briefly

- **One Textual app** in `cli-studio.py`. State is a small dict; navigation
  is a `home` / `about` / `themes` / `menu` / `settings` state machine with
  `Alt+B` going back one level.
- **Wizard pattern** in `workflows/`: every tool is a chain of step closures
  that thread a `state` dict through modal screens. Two helpers
  (`file_in_out_flow`, `file_file_in_out_flow`) cover most tools; the rest
  are inline closures.
- **Backend registry** in `workflows/backends/`: each CLI tool (`YtDlpBackend`,
  `PillowBackend`, `WhisperBackend`, ...) owns the command-construction for
  its tool. Workflows ask for the backend by name; tests can swap
  implementations.
- **Workers**: heavy subprocess work runs in Textual's threaded worker.
  Cancellation via `Escape` calls `process.terminate()` on the main thread.
- **Subprocess safety**: every subprocess call uses list-form `argv` (never
  `shell=True`). User paths are wrapped in `os.path.abspath(os.path.expanduser(p))`
  before being passed to any subprocess.

For the full architecture, see `dev_docs/ARCHITECTURE.md` (contributors only).

---

## Tests and quality

- **151 tests pass** in ~17 seconds (`pytest`).
- `ruff check .` and `mypy cli-studio.py config.py studio_themes.py ui/ workflows/`
  both pass cleanly.
- CI matrix: Python 3.10, 3.11, 3.12, 3.13 (`.github/workflows/ci.yml`).
- `SECURITY.md` documents the threat model and what we do and don't promise.
- `dev_docs/CRITICAL_ASSESSMENT.md`, `dev_docs/CRITICAL_ASSESSMENT_part2.md`,
  and `dev_docs/CRITICAL_ASSESSMENT_part3.md` contain the senior-developer
  audit trail (open; not sanitized).
- `pip install .` produces a `cli-studio` (and `cso`) entry point via
  `[project.scripts]` in `pyproject.toml`. The shell-install path remains
  the recommended route for production installs.

---

## License

MIT. See the repo for the full text.