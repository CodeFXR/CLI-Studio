<h1 align="center">CLI-Studio</h1>

<p align="center">
  <img src="https://github.com/user-attachments/assets/aecea44a-aa39-4dec-ade1-1be60b054f7b" alt="cli-studio icon" width="250" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/Built%20With-Textual-00dadf.svg" alt="Built with Textual" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

<p align="center">
  <b>The Ultimate Terminal Media Dashboard</b><br>
  CLI-Studio is an advanced Terminal User Interface (TUI) that abstracts and simplifies powerful command-line media tools (FFmpeg, ImageMagick, yt-dlp, Pillow). It provides an intuitive, menu-driven workflow, allowing users of any level to perform complex video, audio, and image manipulations without ever leaving the terminal.
</p>

<hr>

## Features

- **37+ Integrated Tools:** A massive suite of media manipulation utilities out-of-the-box.
- **Interactive File Explorer:** Visually browse your filesystem to select files and destinations. No more typing absolute paths manually.
- **Auto-Batch Processing:** Select an entire *folder* instead of a file, and CLI-Studio will automatically process every piece of media inside it with live progress bars.
- **Smart Input Autofill:** Integrates `ffprobe` to automatically read file metadata and pre-fill input fields (e.g., automatically finding the exact end timestamp of a video for precise trimming).
- **Power User Log Console:** Press `Ctrl+L` at any time to toggle an interactive debug log that reveals the exact raw CLI commands being executed under the hood.
- **Integrated Help System:** Press `?` on any tool to open a clear, plain-English explanation of what it does and how to use it.
- **Dynamic Theming Engine:** 8 built-in aesthetic themes (Modern, Hunter, Coppice, Navy, etc.) that save to your preferences.

## Tool Capabilities

### Video Tools (`ffmpeg` & `yt-dlp`)
- **Download Media:** Fetch single videos or entire playlists.
- **Convert & Scale:** Transcode to MP4, MKV, AVI, WebM. Resize resolutions instantly.
- **Edit & Manipulate:** Trim precisely, extract audio, mute, rotate, reverse time, or change playback speed.
- **Advanced Filtering:** Create optimized GIFs, add image watermarks, fade in/out, or mux new audio tracks.

### Audio Tools (`ffmpeg`)
- **Convert & Trim:** Transcode to MP3, WAV, FLAC, AAC, OGG. Slice precise segments.
- **Professional Polish:** Normalize audio levels (`loudnorm`), adjust volume multipliers, or mix multiple tracks together simultaneously.

### Image Tools (`Pillow`, `ImageMagick`, `ExifTool`)
- **Batch Convert & Resize:** Rapidly process folders of images. High-quality Lanczos resampling.
- **Creative Edits:** Remove solid background colors, apply aesthetic filters (Sepia, Charcoal, Negate), flip, crop, or add borders.
- **Privacy & Utility:** Strip all tracking/GPS metadata from media, or instantly convert an entire folder of images into a single, multi-page PDF document.

---

## Installation

CLI-Studio is designed to be installed globally on **Linux** or **macOS**. Our automated bash script handles installing all necessary system dependencies (FFmpeg, ImageMagick, ExifTool), sets up an isolated Python environment, and creates global command aliases.

Run this single command in your terminal:

```bash
curl -fsSL https://cso.codefxr.com/install | bash
```

### Usage
Once installed, you can launch the dashboard from anywhere using either the full name or the acronym shortcut:

```bash
cli-studio
# OR
cso
```

## Global Keybindings

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `?` | **Help** | Open the manual/explanation for the current tool |
| `Ctrl` + `l` | **Log Console** | Toggle the raw execution log view |
| `Alt` + `m` | **Menu** | Open the main tools menu |
| `Alt` + `t` | **Themes** | Open the theme selection screen |
| `Alt` + `b` | **Back** | Return to the previous screen |
| `Alt` + `e` | **Exit** | Close the application |
| `Esc` | **Home / Cancel** | Go to Home screen or close current modal |

---

<p align="center">
  &copy; CodeFXR. All rights reserved.
</p>
