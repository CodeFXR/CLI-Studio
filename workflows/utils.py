import os
import subprocess


SUBTITLE_EXT_MAP = {
    "subrip": "srt",
    "s_text": "srt",
    "mov_text": "srt",
    "ass": "ass",
    "ssa": "ass",
    "webvtt": "vtt",
}


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")


def abspath(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))


def unique_path(directory: str, stem: str, ext: str) -> str:
    """Return a path inside `directory` whose stem does not collide with an existing file.

    For `stem="clip"` and `ext=".mp4"`, returns `directory/clip.mp4` if it does not
    exist, else `directory/clip_2.mp4`, `clip_3.mp4`, and so on. Used by batch
    progress screens to avoid overwriting outputs when two input folders
    contain files with the same name.
    """
    if not ext.startswith("."):
        ext = "." + ext
    candidate = os.path.join(directory, stem + ext)
    counter = 1
    while os.path.lexists(candidate):
        counter += 1
        candidate = os.path.join(directory, f"{stem}_{counter}{ext}")
    return candidate


def get_media_duration(filepath):
    expanded = os.path.abspath(os.path.expanduser(filepath))
    if not os.path.isfile(expanded):
        raise FileNotFoundError(f"Input file not found: {expanded}")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        expanded,
    ]
    try:
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"ffprobe timed out reading {expanded}. "
            "File may be on slow storage or path is unreachable."
        )
    except FileNotFoundError:
        raise RuntimeError("ffprobe not found. Please install ffmpeg.")

    try:
        duration = float(res.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Could not parse duration from {expanded}.")

    total_s = round(duration)
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def probe_first_subtitle_codec(video_path: str) -> str:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    if res.returncode != 0:
        return ""
    lines = res.stdout.strip().splitlines()
    return lines[0].strip().lower() if lines else ""


def subtitle_ext_for_codec(codec: str) -> str:
    if not codec:
        return "srt"
    return SUBTITLE_EXT_MAP.get(codec.lower(), codec.lower())
