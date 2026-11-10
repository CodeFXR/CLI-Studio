<h1 align="center">CLI-Studio</h1>

<p align="center">
  <img src="https://github.com/user-attachments/assets/aecea44a-aa39-4dec-ade1-1be60b054f7b" alt="cli-studio icon" width="250" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/Built%20With-Textual-00dadf.svg" alt="Built with Textual" />
  <img src="https://img.shields.io/badge/Tools-62%20CLI%20Utilities-orange.svg" alt="Tools" />
  <img src="https://img.shields.io/badge/Tests-146%20Passed-success.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/Type%20Safety-Mypy%20Strict-blue.svg" alt="Type Safety" />
  <img src="https://img.shields.io/badge/Code%20Style-Ruff-000000.svg" alt="Code Style" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

<p align="center">
  <b>A Terminal Media Dashboard for Video, Audio, and Image Manipulation</b><br>
  CLI-Studio wraps standard command-line tools (FFmpeg, yt-dlp, Pillow, ImageMagick, ExifTool, tesseract, and mkvtoolnix) behind a menu-driven, keyboard-first terminal user interface. It provides transparent batch execution, live process logging, and context-aware help without leaving the terminal.
</p>

<hr>

## Core Capabilities

- **62 Integrated Tools:** Dedicated video, audio, image, cloud, and preset workflows.
- **Directory Batch Processing:** Selecting a folder instead of a single file automatically processes all matching media with live batch progress.
- **Interactive File Picker:** Navigate the filesystem visually to pick inputs and destination folders.
- **Transparent Execution:** Press `Ctrl+L` at any point to inspect the raw CLI commands and subprocess output in real time.
- **Inline Help (`?`):** Press `?` on any menu item for a plain-English explanation of the tool and its flags.
- **Non-blocking Workers:** Subprocesses run in dedicated worker threads with clean two-phase cancellation (`SIGTERM` followed by `SIGKILL` escalation).
- **Atomic Configuration:** Preferences and settings persist safely in `~/.cli-studio/config.json`.
- **Extensible:** Drop a Python plugin script into `~/.cli-studio/plugins/` to register custom commands.

---

## Installation

CLI-Studio is supported on **Linux** and **macOS**. The installer configures system packages, clones the repository into `~/.cli-studio/`, creates an isolated Python virtual environment, and installs global command wrappers (`cli-studio` and `cso`).

```bash
curl -fsSL https://cso.codefxr.com/install | bash
```

### What the installer does

1. Installs native media tools via your package manager (`apt`, `dnf`, `pacman`, or `brew`).
2. Clones the repository into `~/.cli-studio/`.
3. Creates a private Python virtual environment with dependencies (`textual`, `Pillow`, `yt-dlp`, `natsort`, `textual-image`).
4. Creates executable launchers in `~/.local/bin/cli-studio` and `~/.local/bin/cso`.
5. Prompts to add `~/.local/bin` to your shell profile if it is not already in `$PATH`.

### Launching

Run either command from your terminal:

```bash
cli-studio
# or
cso
```

To update Python dependencies later:

```bash
cli-studio update
```

### System Packages Installed

| Tool | Debian / Ubuntu | Fedora | Arch | macOS (Homebrew) |
| :--- | :--- | :--- | :--- | :--- |
| FFmpeg | `ffmpeg` | `ffmpeg` | `ffmpeg` | `ffmpeg` |
| ImageMagick | `imagemagick` | `ImageMagick` | `imagemagick` | `imagemagick` |
| ExifTool | `libimage-exiftool-perl` | `perl-Image-ExifTool` | `perl-image-exiftool` | `exiftool` |
| Tesseract | `tesseract-ocr tesseract-ocr-eng` | `tesseract` | `tesseract` | `tesseract` |
| MKVToolNix | `mkvtoolnix` | `mkvtoolnix` | `mkvtoolnix` | `mkvtoolnix` |
| ZBar | `zbar-tools` | `zbar` | `zbar` | `zbar` |
| Perl Rename | `rename` | `perl-File-Rename` | `perl-rename` | `rename` |
| Rclone | `rclone` | `rclone` | `rclone` | `rclone` |
| HandBrake CLI | `handbrake-cli` | `HandBrake-cli` | `handbrake-cli` | `handbrake` |
| Chafa | `chafa` | `chafa` | `chafa` | `chafa` |

---

## Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `?` | **Help** | Open the reference manual for the highlighted tool |
| `Ctrl` + `l` | **Log Console** | Toggle live execution logs and raw subprocess output |
| `Alt` + `m` | **Menu** | Open the tool navigation menu |
| `Alt` + `t` | **Themes** | Select from 8 built-in terminal color palettes |
| `Alt` + `s` | **Settings** | Configure browser cookies, hardware acceleration, and defaults |
| `Alt` + `a` | **About** | View application metadata and diagnostics |
| `Alt` + `b` | **Back** | Navigate back to the previous screen |
| `Alt` + `e` | **Exit** | Exit the application |
| `Esc` | **Home / Dismiss** | Dismiss modal dialogs or return to the main dashboard |
| `Ctrl` + `c` | **Quit** | Force-terminate the application |

Quick commands are also available via the command prompt:
```
/home     /menu     /about     /themes     /settings     /exit
/video    /audio    /image     /cloud      /devices      /back
/themes <name>   (e.g. /themes navy)
```

---

## Tool Breakdown (62 Utilities)

### Video Tools (`ffmpeg`, `yt-dlp`, `mkvtoolnix`, `HandBrakeCLI`)
- **Download:** Download individual videos, complete playlists, or galleries.
- **Conversion & Presets:** Convert between MP4, MKV, WebM, AVI; apply 16 HandBrake device presets (Apple, Android, Roku, etc.).
- **Editing:** Precision trimming, audio extraction, video muting, speed adjustment, rotation, and reversal.
- **Effects & Filters:** High-quality GIF creation, frame extraction, image watermarking, secondary audio muxing, scaling, fade transitions, and audio visualization.
- **Subtitles & AI:** Subtitle extraction, subtitle burn-in, and local subtitle generation via Whisper.
- **MKV Management:** Native stream parsing, attachment extraction, and lossless remuxing.

### Audio Tools (`ffmpeg`, `ffmpeg-normalize`)
- **Conversion & Trimming:** Transcode across MP3, WAV, FLAC, AAC, OGG, OPUS; trim by timestamps.
- **Mastering:** Standard normalization, 2-pass EBU R128 normalization (`ffmpeg-normalize`), volume scaling, speed adjustment, fade effects, track mixing, and waveform previews.

### Image Tools (`Pillow`, `ImageMagick`, `ExifTool`, `tesseract`, `zbarimg`, `chafa`)
- **Basic Editing:** Format conversion, Lanczos resampling, rectangular cropping, rotation, flip, borders, and multi-image sprite sheet generation.
- **Color & Creative:** Color replacement, solid background removal, filter presets (Sepia, Charcoal, Negate, etc.), and text watermarking.
- **Metadata & OCR:** Metadata stripping, EXIF tag editing, EXIF copying, file renaming by EXIF capture date, optical character recognition (OCR), and barcode/QR scanning.
- **Terminal Previews:** In-terminal graphic previewing via Chafa.

### Cloud Storage (`rclone`)
- **Operations:** Cloud synchronization, copying, and remote bucket inspection.

---

## Settings & Privacy

Open settings using `Alt+S` or `/settings`. All options persist in `~/.cli-studio/config.json`.

| Setting | Default | Description |
| :--- | :--- | :--- |
| `yt_dlp_cookies` | `""` (Disabled) | Browser profile to extract session cookies from (e.g. `firefox`, `chrome`). |
| `yt_dlp_remote_components` | `""` (Disabled) | Explicit yt-dlp remote components flag. |
| `hw_accel` | `""` (Software) | Hardware encoding engine (`nvenc`, `vaapi`, `videotoolbox`, `qsv`). |
| `ffmpeg_overwrite` | `true` | Overwrites destination files when enabled; uses `-n` when disabled. |
| `whisper_model` | `small` | faster-whisper model weight (`tiny`, `base`, `small`, `medium`, `large-v3`). |
| `whisper_device` | `auto` | Execution device (`auto`, `cpu`, `cuda`). |
| `whisper_compute` | `auto` | Quantization precision (`auto`, `int8`, `float16`, `float32`). |
| `whisper_cache_dir` | `~/.cache/cli-studio/whisper` | Local storage location for downloaded model weights. |
| `enable_plugins` | `false` | Security toggle required to load scripts from `~/.cli-studio/plugins/`. |

---

## Security & Verification

- **Subprocess Safety:** All system commands use array-based argument vectors (zero `shell=True`).
- **Path Sanitization:** User paths are expanded and canonicalized with symlink clobber protection.
- **Process Escalation:** Subprocesses cleanly terminate via `SIGTERM` with an automated `SIGKILL` escalation fallback.
- **Input Validation:** Numeric ranges, dimensions, and timestamps are strictly validated against bounds before execution.
- **Test Suite:** 168 automated unit, regression, and integration tests passing (`pytest`).
- **Code Quality:** Strict type-checked (`mypy`) and linted (`ruff`) with zero warnings.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
