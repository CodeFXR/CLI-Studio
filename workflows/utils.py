import os
import subprocess


SUBTITLE_EXT_MAP = {
    "subrip": "srt",
    "s_text": "srt",
    "mov_text": "srt",
    "text": "srt",
    "ass": "ass",
    "ssa": "ass",
    "webvtt": "vtt",
    "hdmv_pgs_subtitle": "sup",
    "dvd_subtitle": "sub",
}


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")


def abspath(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))


def file_arg(path: str) -> str:
    """Return `path` as a safe positional file argument for a CLI tool.

    F-1: option termination cannot rest on callers remembering to
    absolutize paths. Builders call this so the invariant lives in one
    place: the returned path is absolute, therefore it can never be
    parsed as an option by ffmpeg / ImageMagick / chafa / realesrgan,
    none of which reliably honour "--" in every position (verified on
    ffmpeg 8.1.2: `ffmpeg -i -- -file.mp4` FAILS with "Unrecognized
    option"; `ffprobe ... -- -file.mp4` works, and the ffprobe call
    sites below use both defences). Raises ValueError for empty paths
    and for NUL/newline, which no wrapped tool accepts in a filename
    argument anyway.
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("File path cannot be empty.")
    if "\x00" in path or "\n" in path or "\r" in path:
        raise ValueError(f"File path contains illegal characters: {path!r}")
    return os.path.abspath(os.path.expanduser(path))


def escape_subtitles_filter_arg(sub_path: str) -> str:
    """Build the ffmpeg `subtitles=` filter argument for a subtitle path.

    F-3: this escaper used to live hand-rolled and untested in
    workflows/video.py. It now lives here (stdlib-only, unit-testable
    without Textual) with its behaviour pinned by tests in
    tests/test_v14_fixes.py. The per-character table was verified
    against real ffmpeg 8.1.2 filter parsing for 21 adversarial
    filenames (spaces, colon, apostrophe, comma, brackets, semicolon,
    '=', '"', backslash, colon+backslash mixes, trailing backslash,
    percent, unicode) -- every one parsed and opened the correct
    file, so the algorithm is KEPT, not replaced. (Newline in a path
    also parsed under the old code; file_arg now rejects it up front,
    which is the safer behaviour for a wizard-driven tool.) Do not
    "simplify" it to a quote-wrapping scheme: the obvious single-quote
    variant was also tested and fails on colon/apostrophe/backslash
    paths (8/12 vectors). If ffmpeg's escaping rules change, the
    ffmpeg-backed integration test in the test file is the canary.
    """
    expanded = file_arg(sub_path)
    res = []
    for ch in expanded:
        if ch == "\\":
            res.append("\\\\\\\\")
        elif ch == "'":
            res.append("\\\\\\'")
        elif ch == ":":
            res.append("\\\\:")
        elif ch in (",", "[", "]", ";", " ", '"', "="):
            res.append("\\" + ch)
        else:
            res.append(ch)
    return f"subtitles=filename={''.join(res)}:si=0"


def open_output_nofollow(path: str):
    """Open a text output file for writing WITHOUT following a symlink.

    F-10: the app's pattern was islink(path) -> ... -> open(path, "w"),
    a check-then-write TOCTOU window, applied inconsistently. Opening
    with O_NOFOLLOW makes the check atomic with the write: if the final
    path component is a symlink (planted, dangling, or swapped in after
    any earlier check), os.open raises OSError(ELOOP) instead of
    clobbering the link target. Parent directory must already exist.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o644)
    return os.fdopen(fd, "w", encoding="utf-8")


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
    expanded = file_arg(filepath)
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
        "--",
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
        "--",
        file_arg(video_path),
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


def probe_has_audio(video_path: str) -> bool:
    """Return True if the media file contains at least one audio stream."""
    if not video_path or not os.path.isfile(video_path):
        return True
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        "--",
        file_arg(video_path),
    ]
    try:
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return bool(res.stdout.strip())
    except Exception:
        return True
