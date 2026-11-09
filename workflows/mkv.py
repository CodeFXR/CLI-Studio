import json
import os
import re
import subprocess
from natsort import natsorted
from ui.screens import FilePickerScreen, OptionSelectScreen
from ui.progress import GenericCliProgressScreen
from workflows.utils import file_arg


def _probe_subtitle_tracks(mkv_path: str) -> list[dict]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language",
        "-of",
        "json",
        "--",
        file_arg(mkv_path),
    ]
    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if res.returncode != 0:
        return []
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return []
    out = []
    for stream in data.get("streams", []):
        out.append(
            {
                "index": int(stream.get("index", 0)),
                "codec_name": (stream.get("codec_name") or "").lower(),
                "language": stream.get("tags", {}).get("language", "") or "",
            }
        )
    return out


def _probe_attachments(mkv_path: str) -> list[dict]:
    """Enumerate attachments in an MKV (fonts, images, etc.).

    Queries mkvmerge -J to retrieve the exact native Matroska attachment IDs
    required by mkvextract. Only entries that carry a valid integer attachment
    id are included with their id set.

    If mkvmerge is not installed on the system (FileNotFoundError), falls back to ffprobe
    to discover attachment filenames and metadata for UI display, with
    "id" set to None so mkvextract is never invoked with fabricated IDs.
    Returns a list of dicts: {"id": int | None, "filename": str, "mimetype": str, "size": int}.
    """
    cmd_mkv = ["mkvmerge", "-J", file_arg(mkv_path)]
    try:
        res = subprocess.run(cmd_mkv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        # mkvmerge is not installed on this system; fall back to ffprobe for display-only
        res = None
    except Exception:
        # Timeouts, OS errors, etc. when mkvmerge is present return empty, never fall back
        return []

    if res is not None:
        if res.returncode != 0:
            return []
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return []
        raw_atts = data.get("attachments", [])
        out = []
        for att in raw_atts:
            id_val = att.get("id")
            if id_val is None:
                continue
            try:
                int_id = int(id_val)
            except (ValueError, TypeError):
                continue
            fn = att.get("filename") or att.get("file_name") or f"attachment_{int_id}"
            mt = att.get("mimetype") or att.get("content_type", "")
            try:
                sz = int(att.get("size", 0) or 0)
            except (ValueError, TypeError):
                sz = 0
            out.append(
                {
                    "id": int_id,
                    "filename": fn,
                    "mimetype": mt,
                    "size": sz,
                }
            )
        return out

    # Fallback to ffprobe ONLY when mkvmerge binary is not found (display only, id=None)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        "--",
        file_arg(mkv_path),
    ]
    try:
        res_ff = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if res_ff.returncode != 0:
        return []
    try:
        data = json.loads(res_ff.stdout)
    except json.JSONDecodeError:
        return []

    attachments: list[dict] = []
    att_idx = 1
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "attachment":
            tags = stream.get("tags", {})
            filename = tags.get("filename") or f"attachment_{att_idx}"
            mimetype = tags.get("mimetype") or ""
            try:
                size = int(tags.get("NUMBER_OF_BYTES", 0) or 0)
            except (ValueError, TypeError):
                size = 0
            attachments.append(
                {
                    "id": None,
                    "filename": filename,
                    "mimetype": mimetype,
                    "size": size,
                }
            )
            att_idx += 1

    return attachments


def build_remux_to_mkv_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        base, ext = os.path.splitext(in_file)
        default_out = f"{base}_remux.mkv" if ext.lower() == ".mkv" else f"{base}.mkv"
        return FilePickerScreen("Save MKV As:", default_out, state, step3)

    def step3(out_file, state):
        cmd = ["mkvmerge", "-o", file_arg(out_file), file_arg(state["in_file"])]
        return GenericCliProgressScreen(cmd, "mkvmerge", out_file)

    return FilePickerScreen("Select Video File:", "", {}, step2)


def build_merge_mkvs_flow():
    """Concatenate multiple MKV files (no re-encoding) into one MKV using mkvmerge.

    Folder input gets natsorted; each input is passed with a `+` separator so mkvmerge
    treats them as a sequence to append, not separate tracks.
    """

    def step2(in_path, state):
        state["in_path"] = in_path
        abs_in = file_arg(in_path)
        if os.path.isdir(abs_in):
            files = [f for f in os.listdir(abs_in) if f.lower().endswith((".mkv", ".mka", ".mks"))]
            files = natsorted(files)
            files = [os.path.join(abs_in, f) for f in files]
        else:
            files = [abs_in]
        state["files"] = files
        return FilePickerScreen(
            "Save Merged MKV As:", f"{os.path.expanduser('~')}/merged.mkv", state, step3
        )

    def step3(out_file, state):
        files = state["files"]
        if not files:
            return None
        expanded_out = file_arg(out_file)
        if len(files) == 1:
            cmd = ["mkvmerge", "-o", expanded_out, file_arg(files[0])]
        else:
            cmd = ["mkvmerge", "-o", expanded_out]
            for i, f in enumerate(files):
                if i:
                    cmd.append("+")
                cmd.append(file_arg(f))
        return GenericCliProgressScreen(cmd, "mkvmerge", expanded_out)

    return FilePickerScreen("Select Folder of MKVs (or single MKV):", "", {}, step2)


def build_extract_mkv_subs_flow():
    """Run ffprobe to discover subtitle tracks, then run mkvextract for each one.

    Subtitle files are saved with a `_LANG` suffix when a language tag is present,
    otherwise `_N` where N is the track index. No re-encoding.
    """

    def step2(in_file, state):
        state["in_file"] = in_file
        tracks = _probe_subtitle_tracks(file_arg(in_file))
        state["tracks"] = tracks
        return FilePickerScreen(
            "Save directory (subs named <base>_<lang-or-idx>.<ext>):",
            os.path.expanduser("~"),
            state,
            step3,
        )

    def step3(out_dir, state):
        tracks = state["tracks"]
        if not tracks:
            return None
        in_abs = file_arg(state["in_file"])
        base, _ = os.path.splitext(os.path.basename(state["in_file"]))
        expanded_out_dir = file_arg(out_dir)
        os.makedirs(expanded_out_dir, exist_ok=True)
        ext_map = {
            "subrip": "srt",
            "s_text": "srt",
            "ass": "ass",
            "ssa": "ass",
            "webvtt": "vtt",
            "mov_text": "srt",
        }
        cmds = []
        used_sub_names: set[str] = set()
        for t in tracks:
            t_id = t["index"]
            codec = t["codec_name"] or "srt"
            ext = ext_map.get(codec, codec)
            raw_lang = t.get("language") or ""
            safe_lang = re.sub(r"[^\w-]", "", raw_lang)
            suffix = f"_{safe_lang}" if safe_lang else f"_{t_id}"
            raw_sub_name = f"{base}{suffix}.{ext}"
            out_filename = os.path.basename(raw_sub_name).lstrip(".")
            if not out_filename:
                out_filename = f"sub_{t_id}.{ext}"
            stem, sub_ext = os.path.splitext(out_filename)
            candidate = out_filename
            counter = 1
            out_file = os.path.normpath(os.path.join(expanded_out_dir, candidate))
            while os.path.lexists(out_file) or candidate.lower() in used_sub_names:
                candidate = f"{stem}_{counter}{sub_ext}"
                counter += 1
                out_file = os.path.normpath(os.path.join(expanded_out_dir, candidate))
            used_sub_names.add(candidate.lower())

            if os.path.commonpath([expanded_out_dir, out_file]) != expanded_out_dir:
                out_file = os.path.join(expanded_out_dir, f"sub_{t_id}.{ext}")
            cmds.append(["mkvextract", "tracks", in_abs, f"{t_id}:{out_file}"])
        if not cmds:
            return None
        return GenericCliProgressScreen(cmds, "mkvextract", expanded_out_dir)

    return FilePickerScreen("Select MKV File:", "", {}, step2)


_MKV_SUB_LANGS = ["eng", "deu", "fra", "spa", "ita", "jpn", "und (no tag)"]


def build_add_subtitles_to_mkv_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return FilePickerScreen("Select Subtitle File (.srt/.ass/.vtt):", "", state, step3)

    def step3(sub_file, state):
        state["sub_file"] = sub_file
        return OptionSelectScreen("Subtitle language tag:", _MKV_SUB_LANGS, state, step4)

    def step4(lang, state):
        state["lang"] = lang
        base, _ = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save MKV As:", f"{base}_with_subs.mkv", state, step5)

    def step5(out_file, state):
        in_abs = file_arg(state["in_file"])
        sub_abs = file_arg(state["sub_file"])
        out_abs = file_arg(out_file)
        lang = state["lang"]
        if lang.startswith("und"):
            cmd = ["mkvmerge", "-o", out_abs, in_abs, sub_abs]
        else:
            cmd = ["mkvmerge", "-o", out_abs, in_abs, "--language", f"0:{lang}", sub_abs]
        return GenericCliProgressScreen(cmd, "mkvmerge", out_abs)

    return FilePickerScreen("Select MKV File:", "", {}, step2)


def build_extract_mkv_attachments_flow():
    """Extract attachments (fonts, images) from an MKV using mkvextract attachments.

    Pre-flights with mkvmerge -J to enumerate attachments and their native Matroska IDs;
    outputs are saved with their sanitized filenames into a chosen directory.
    """

    def step2(in_file, state):
        state["in_file"] = in_file
        attachments = _probe_attachments(file_arg(in_file))
        state["attachments"] = attachments
        return FilePickerScreen(
            "Save directory (attachments named per their original filenames):",
            os.path.expanduser("~"),
            state,
            step3,
        )

    def step3(out_dir, state):
        attachments = state["attachments"]
        if not attachments:
            return None
        in_abs = file_arg(state["in_file"])
        expanded_out_dir = file_arg(out_dir)
        os.makedirs(expanded_out_dir, exist_ok=True)
        cmds = []
        used_names: set[str] = set()
        for idx, att in enumerate(attachments, 1):
            raw_filename = att.get("filename") or f"attachment_{idx}"
            safe_name = os.path.basename(raw_filename.replace("\\", "/")).strip()
            safe_name = re.sub(r"[^\w\s.-]", "_", safe_name).strip()
            # Strip leading dots to prevent planting hidden files (e.g. .bashrc, .profile)
            safe_name = safe_name.lstrip(".")
            if not safe_name or safe_name in (".", ".."):
                safe_name = f"attachment_{idx}"
            stem, ext = os.path.splitext(safe_name)
            candidate = safe_name
            counter = 1
            out_file = os.path.normpath(os.path.join(expanded_out_dir, candidate))
            while os.path.lexists(out_file) or candidate.lower() in used_names:
                candidate = f"{stem}_{counter}{ext}"
                counter += 1
                out_file = os.path.normpath(os.path.join(expanded_out_dir, candidate))
            used_names.add(candidate.lower())
            if os.path.commonpath([expanded_out_dir, out_file]) != expanded_out_dir:
                out_file = os.path.join(expanded_out_dir, f"attachment_{idx}")
            att_id = att.get("id")
            if not isinstance(att_id, int):
                continue
            cmds.append(["mkvextract", "attachments", in_abs, f"{att_id}:{out_file}"])
        if not cmds:
            return None
        return GenericCliProgressScreen(cmds, "mkvextract", expanded_out_dir)

    return FilePickerScreen("Select MKV File:", "", {}, step2)
