import json
import os
import re
import tempfile

MENU_MAIN = [
    "Video Tools",
    "Audio Tools",
    "Image Tools",
    "Device Presets",
    "Cloud Tools",
    "Settings",
]
MENU_SETTINGS = [
    "yt-dlp Cookies",
    "yt-dlp Remote Components",
    "Hardware Acceleration",
    "FFmpeg Overwrite",
    "Whisper Model",
    "Whisper Device",
    "Whisper Compute",
    "Whisper Cache Directory",
]
MENU_VIDEO = [
    "Download Video",
    "Download Playlist",
    "Download Gallery",
    "Convert Video",
    "Trim Video",
    "Extract Audio",
    "Mute Video",
    "Change Video Speed",
    "Rotate Video",
    "Reverse Video",
    "Create GIF",
    "Extract Frames",
    "Add Watermark",
    "Add Audio Track",
    "Scale/Resize Video",
    "Fade In Video",
    "Extract Subtitles",
    "Generate Whisper Subtitles",
    "Burn Subtitles",
    "Silence Removal",
    "Audio Visualizer",
    "Convert Video Preset",
    "Remux Video to MKV",
    "Merge MKVs",
    "Extract MKV Subs",
    "Add Subs to MKV",
    "Extract MKV Attachments",
]
MENU_AUDIO = [
    "Download Audio",
    "Convert Audio",
    "Trim Audio",
    "Change Volume",
    "Change Audio Speed",
    "Reverse Audio",
    "Normalize Audio",
    "Fade In Audio",
    "Mix Audio Tracks",
    "Preview Audio Waveform",
    "Normalize Audio (2-pass)",
]
MENU_IMAGE = [
    "Convert Image",
    "Resize Image",
    "Crop Image",
    "Rotate Image",
    "Flip Image",
    "Remove Background Color",
    "Apply Filter",
    "Strip Metadata",
    "Add Text Watermark",
    "Optimize/Compress",
    "Convert to PDF",
    "Add Border",
    "Extract Text from Image",
    "Preview Image",
    "Upscale Image",
    "Sprite Sheet",
    "Set EXIF Tag",
    "Copy EXIF",
    "Rename by EXIF Date",
    "Scan Barcode",
]
MENU_DEVICES = [
    "Transcode Device Preset",
    "List HandBrake Presets",
]

MENU_CLOUD = [
    "Rclone Copy",
    "Rclone List Remotes",
]

MENUS = {
    "main": MENU_MAIN,
    "video": MENU_VIDEO,
    "audio": MENU_AUDIO,
    "image": MENU_IMAGE,
    "devices": MENU_DEVICES,
    "cloud": MENU_CLOUD,
    "settings": MENU_SETTINGS,
}

HELP_REGISTRY = {
    "download video": "Downloads a video from a URL (YouTube, Vimeo, etc.) to your local machine.",
    "download audio": "Downloads audio from a URL (YouTube, Vimeo, etc.) and saves it directly as MP3. Skips the video stream entirely.",
    "download playlist": "Downloads all videos in a specified YouTube/Vimeo playlist.",
    "convert video": "Transcodes a video file to a different container (mp4/mkv/avi/webm/mov) using default settings. For codec and preset control, use 'Convert Video (Preset)'.",
    "convert audio": "Transcodes an audio file to a different format (mp3/wav/flac/aac/ogg). Re-encodes the audio stream with sensible defaults.",
    "extract audio": "Strips the video stream and saves only the audio track as an MP3.",
    "trim video": "Cuts a segment of the video. Enter start and end times in seconds or HH:MM:SS format.\nExample: Start 00:01:00, End 00:02:00 extracts 1 minute.",
    "trim audio": "Cuts a segment of the audio track. Uses precise timestamps to extract exactly what you need without re-encoding.",
    "mute video": "Removes the audio track from a video without re-encoding the video stream (-c:v copy -an).",
    "change video speed": "Speeds up or slows down the video while maintaining audio sync (where atempo supports the speed range).",
    "change audio speed": "Speeds up or slows down audio playback. Uses atempo (range 0.5x to 2.0x per filter; chained internally for higher ratios).",
    "change volume": "Multiplies the audio volume by a factor (e.g. 2.0 = 200%, 0.5 = 50%).",
    "rotate video": "Rotates a video 90° (clockwise/counter-clockwise) or 180°. Uses the ffmpeg transpose filter.",
    "rotate image": "Rotates an image by 90, 180, or 270 degrees.",
    "reverse video": "Reverses the video and audio streams so the file plays backwards. Re-encodes both streams.",
    "reverse audio": "Reverses the audio stream so the file plays backwards. Re-encodes the audio.",
    "create gif": "Converts a short video into an animated GIF at 320px width and 10 fps.",
    "extract frames": "Extracts still frames from a video at a chosen FPS. The output pattern must contain `%d` (e.g. `clip_%03d.png`).",
    "scale/resize video": "Resizes a video. Enter resolution as W:H (e.g. 1920:1080 or 1280:-1 to keep aspect ratio).",
    "fade in video": "Adds a fade-in effect from black at the start of the video. Enter the fade duration in seconds.",
    "fade in audio": "Fades the audio in from silence at the start. Enter the fade duration in seconds.",
    "extract subtitles": "Extracts the first subtitle stream from a video as a separate file. The output extension is auto-detected (srt/ass/vtt).",
    "mix audio tracks": "Combines two audio files into a single stereo track using ffmpeg's amix filter.",
    "add audio track": "Replaces (or adds) an audio track in a video. Picks the first video stream from the input and the first audio stream from the chosen audio file. Re-encodes audio to AAC.",
    "add border": "Adds a solid black border of the given pixel width around an image.",
    "convert image": "Changes the file format of an image (e.g., from PNG to JPG). Automatically handles transparency.",
    "crop image": "Crops an image to the given Left,Top,Right,Bottom box.",
    "flip image": "Flips an image horizontally (mirror) or vertically.",
    "add text watermark": "Draws the given text in white at position (20, 20) on the image. Pillow-based.",
    "optimize/compress": "Re-encodes an image as JPEG with the given quality (1-100). Smaller files at lower quality.",
    "resize image": "Changes the dimensions of an image using high-quality Lanczos resampling.\nEnter resolution as WidthxHeight (e.g. 1920x1080).",
    "remove background color": "Deletes a solid background color from an image, making it transparent. Uses ImageMagick's fuzz factor to handle slight gradients.",
    "apply filter": "Applies a predefined aesthetic filter to your image using ImageMagick.",
    "strip metadata": "Removes all EXIF, GPS, and tracking data from an image or video for privacy.",
    "add watermark": "Overlays a second image (like a PNG logo) onto a video in the bottom right corner.",
    "normalize audio": "Levels out audio so quiet parts are louder and loud parts are softer. Great for podcasts.",
    "convert to pdf": "Combines a folder of images into a single, multi-page PDF document.",
    "extract text from image": "Runs OCR (tesseract) on an image and writes the recognized text to a .txt file. Pick a language (eng/deu/fra/spa/ita).",
    "preview image": "Preview an image inside the TUI using chafa. Requires the chafa system command.",
    "upscale image": "Upscale an image with the Real-ESRGAN ncnn Vulkan command-line tool. Put `realesrgan-ncnn-vulkan` and its model files on PATH before running this tool.",
    "remux video to mkv": "Re-wraps any video container into MKV without re-encoding using mkvmerge. Preserves all original streams.",
    "merge mkvs": "Concatenates multiple MKV files into one using mkvmerge with the `+` separator. Files in a folder are processed in natsort order (1.mkv, 2.mkv, 10.mkv).",
    "extract mkv subs": "Runs ffprobe to discover subtitle tracks in an MKV, then extracts each one with mkvextract. Files are saved with `_LANG` or `_N` suffixes in a chosen directory.",
    "add subs to mkv": "Muxes a subtitle file (.srt/.ass/.vtt) into an existing MKV without re-encoding. Saves as a new MKV preserving all original tracks.",
    "extract mkv attachments": "Extracts bundled attachments (fonts, images) from an MKV using mkvextract. Files are saved with their original filenames in a chosen directory. Useful for grabbing fonts a video references.",
    "convert video preset": "Transcode a video with explicit codec + preset selection. Pick the format (mp4/mkv/avi/webm/mov), the codec (libx264 / libx265 / libsvtav1 / copy — or a hardware encoder when `hw_accel` is set in config), and the preset (slower presets = better compression; `copy` skips re-encoding). Valid `hw_accel` values: `nvenc`, `vaapi`, `videotoolbox`, `qsv`.",
    "generate whisper subtitles": "Generates SRT or VTT subtitles from audio or video with optional faster-whisper models. Install with `pip install 'faster-whisper>=1.0'` before use.",
    "burn subtitles": "Bake a subtitle file (.srt/.ass) into a video as hardcoded subs using ffmpeg's `subtitles=` filter. Useful when the player doesn't support soft subs or you want them visible during sharing.",
    "silence removal": "Strip silent stretches from audio using ffmpeg's silenceremove filter. Threshold/duration tuned for typical podcast/speech audio. Adjust via the existing `Extract Audio` flow if needed.",
    "audio visualizer": "Render a 1920x240 waveform PNG from an audio file using ffmpeg's showwaves filter. Useful as a chapter marker or thumbnail.",
    "preview audio waveform": "Preview an audio waveform inside the TUI using chafa. audiowaveform is used when installed, with an ffmpeg fallback.",
    "sprite sheet": "Combine a folder of images into a single sprite sheet via ImageMagick's `magick montage`. Pick a tile grid (2x2 through 6x6 or auto single-row).",
    "set exif tag": "Set a single EXIF/XMP tag on one or more images via exiftool with `-overwrite_original`. Common tags: Copyright, Artist, Description, DateTimeOriginal.",
    "copy exif": "Copy all EXIF metadata from a source image onto a target image via exiftool `-tagsFromFile`. Useful for uniform metadata across a photo set.",
    "rename by exif date": "Rename images in a folder using their EXIF `DateTimeOriginal` (pattern: `YYYY-MM-DD_HHMMSS_original.ext`) via exiftool's `-FileName<DateTimeOriginal` flag.",
    "scan barcode": "Scan QR / barcodes in one or more images using `zbarimg`. Outputs a .txt file with one decoded payload per line (zbarimg's raw format).",
    "download gallery": "Download a gallery / image set from a URL using `gallery-dl`. Supports many sites (Reddit, Imgur, Twitter, Pixiv, etc.). Saves to a chosen directory.",
    "normalize audio (2-pass)": "Two-pass loudness normalization via `ffmpeg-normalize` (the Python wrapper). Default target: -23 LUFS broadcast standard. Upgrades the single-pass `loudnorm` used by the basic `normalize audio` flow.",
    "rclone copy": "Copy a local file or folder to a configured rclone remote. Equivalent to `rclone copy <local> <remote>:<path>`.",
    "rclone list remotes": "List configured rclone remotes via `rclone listremotes --long`. Useful for confirming what you've configured before running a copy.",
    "transcode device preset": "Run HandBrakeCLI with a device preset (Apple/Android/Chromecast/Fire TV/etc.). Beats maintaining a custom CRF library — HandBrake's preset logic is well-maintained.",
    "list handbrake presets": "List all HandBrakeCLI presets installed on this system via `HandBrakeCLI --preset-list`. Outputs a .txt file.",
}


def get_help(cmd):
    return HELP_REGISTRY.get(
        cmd,
        f"Runs the '{cmd}' tool. Follow the on-screen prompts to configure your inputs and execute.",
    )


CONFIG_FILE = os.path.expanduser("~/.cli_studio_config.json")

DEFAULT_CONFIG = {
    "default_theme": "t-default",
    "yt_dlp_cookies": "",
    "yt_dlp_remote_components": "",
    "hw_accel": "",
    "ffmpeg_overwrite": True,
    "whisper_model": "small",
    "whisper_device": "auto",
    "whisper_compute": "auto",
    "whisper_cache_dir": "~/.cache/cli-studio/whisper",
    "enable_plugins": False,
}


def coerce_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _load_full_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_CONFIG)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError) as e:
        if isinstance(e, json.JSONDecodeError):
            try:
                corrupt_backup = f"{CONFIG_FILE}.corrupt"
                if not os.path.exists(corrupt_backup):
                    import shutil
                    shutil.copy2(CONFIG_FILE, corrupt_backup)
            except OSError:
                pass
        return dict(DEFAULT_CONFIG)


def _save_config(config: dict) -> None:
    dir_name = os.path.dirname(CONFIG_FILE) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".cli_studio_config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


_RESOLUTION_RE = re.compile(r"^\d+:-?\d+$")
_DIMENSIONS_RE = re.compile(r"^\d+x\d+$")
_COORDS_RE = re.compile(r"^\d+,\d+,\d+,\d+$")
_DECIMAL_RE = re.compile(r"^\d+(\.\d+)?$")
_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_EXIF_TAG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-:]*$")
_BLOCKED_CACHE_PREFIXES = ("/etc", "/usr", "/sys", "/proc", "/boot", "/var/lib", "/bin", "/sbin")


def validate_resolution(v: str) -> str:
    if not _RESOLUTION_RE.match(v):
        raise ValueError(f"Invalid resolution '{v}'. Use W:H (e.g. 1280:720 or 1920:-1).")
    w_str, h_str = v.split(":")
    w, h = int(w_str), int(h_str)
    if w <= 0 or (h <= 0 and h != -1) or w > 16384 or h > 16384:
        raise ValueError(
            f"Resolution '{v}' is out of bounds. Width must be 1-16384 and height must be -1 or 1-16384."
        )
    return v


def validate_dimensions(v: str) -> tuple[int, int]:
    if not _DIMENSIONS_RE.match(v.lower()):
        raise ValueError(f"Invalid dimensions '{v}'. Use WxH (e.g. 1920x1080).")
    w, h = map(int, v.lower().split("x"))
    if w <= 0 or h <= 0 or w > 16384 or h > 16384:
        raise ValueError(
            f"Dimensions '{v}' are out of bounds. Width and height must be integers between 1 and 16384."
        )
    return w, h


def validate_coords(v: str) -> tuple[int, int, int, int]:
    cleaned = v.replace(" ", "")
    if not _COORDS_RE.match(cleaned):
        raise ValueError(
            f"Invalid coordinates '{v}'. Use Left,Top,Right,Bottom (e.g. 0,0,500,500)."
        )
    left, top, right, bottom = map(int, cleaned.split(","))
    return left, top, right, bottom


def validate_decimal(v: str, min_val: float | None = None, max_val: float | None = None) -> str:
    if not _DECIMAL_RE.match(v):
        raise ValueError(
            f"Invalid number '{v}'. Use digits with optional decimal (e.g. 2.0 or 30)."
        )
    val = float(v)
    if min_val is not None and val < min_val:
        raise ValueError(f"Value '{v}' must be at least {min_val}.")
    if max_val is not None and val > max_val:
        raise ValueError(f"Value '{v}' cannot exceed {max_val}.")
    return v


def validate_quality(v: str) -> str:
    validate_decimal(v, min_val=1, max_val=100)
    return str(int(float(v)))


def validate_remote_name(v: str) -> str:
    if not v.strip():
        raise ValueError("Remote name cannot be empty.")
    if not _REMOTE_NAME_RE.match(v):
        raise ValueError(
            f"Invalid remote name '{v}'. Use letters, digits, '.', '_', or '-' (start with letter or digit)."
        )
    return v


def validate_exif_tag(v: str) -> str:
    if not v.strip():
        raise ValueError("EXIF tag name cannot be empty.")
    if not _EXIF_TAG_RE.match(v):
        raise ValueError(
            f"Invalid EXIF tag '{v}'. Start with a letter; use letters, digits, '.', '_', '-', or ':'."
        )
    return v


def validate_cache_dir(v: str) -> str:
    if not v.strip():
        return ""
    expanded = os.path.realpath(os.path.expanduser(v))
    allowed_roots = [
        os.path.realpath(os.path.expanduser("~")),
        os.path.realpath("/tmp"),
        os.path.realpath("/var/tmp"),
    ]
    if not any(
        expanded == root or expanded.startswith(root.rstrip("/") + "/")
        for root in allowed_roots
    ):
        raise ValueError(
            f"Cache directory '{v}' resolves to '{expanded}'. "
            "Use a path under $HOME, /tmp, or /var/tmp."
        )
    for prefix in _BLOCKED_CACHE_PREFIXES:
        resolved_prefix = os.path.realpath(prefix)
        if expanded == resolved_prefix.rstrip("/") or expanded.startswith(resolved_prefix + "/"):
            raise ValueError(
                f"Cache directory '{v}' resolves to system location '{expanded}'. "
                "Use a path under $HOME, /tmp, or /var/tmp."
            )
    return expanded
