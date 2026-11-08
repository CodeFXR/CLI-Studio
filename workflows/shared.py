import os
from typing import cast

from config import _load_full_config
from ui.progress import DownloadProgressScreen, FfmpegProgressScreen, GenericCliProgressScreen
from ui.screens import FilePickerScreen, OptionSelectScreen, TextInputScreen
from workflows.backends import GalleryDlBackend, get_backend
from workflows.utils import abspath, get_media_duration


def build_download_flow(is_audio: bool, is_playlist: bool = False):
    config = _load_full_config()
    cookies = config.get("yt_dlp_cookies", "")
    remote_components = config.get("yt_dlp_remote_components", "")

    def step2(url, state):
        state["url"] = url
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        return FilePickerScreen("Where to save?", default_path, state, step3)

    def step3(path, state):
        return DownloadProgressScreen(
            state["url"],
            path,
            cookies=cookies,
            remote_components=remote_components,
            is_audio=is_audio,
            is_playlist=is_playlist,
        )

    title = "Enter Playlist URL:" if is_playlist else "Enter URL:"
    return TextInputScreen(title, "Right-click or Ctrl+Shift+V to Paste...", "", {}, step2)


def build_convert_media_flow(is_audio: bool):
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = (
            ["mp3", "wav", "flac", "aac", "ogg"]
            if is_audio
            else ["mp4", "mkv", "avi", "webm", "mov"]
        )
        return OptionSelectScreen("Select Target Format:", opts, state, step3)

    def step3(fmt, state):
        state["fmt"] = fmt
        base = os.path.splitext(state["in_file"])[0]
        return FilePickerScreen(
            "Save As (or select dir for batch):", f"{base}_converted.{fmt}", state, step4
        )

    def step4(out_file, state):
        return FfmpegProgressScreen(state["in_file"], out_file, [], target_ext=state["fmt"])

    return FilePickerScreen("Select Media File/Folder:", "", {}, step2)


def build_trim_media_flow(is_video: bool):
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen("Start Time:", "e.g. 00:01:30 or 90", "00:00:00", state, step3)

    def step3(start, state):
        state["start"] = start
        end_time = get_media_duration(state["in_file"])
        return TextInputScreen("End Time:", "e.g. 00:02:45 or 165", end_time, state, step4)

    def step4(end, state):
        state["end"] = end
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_trimmed{ext}", state, step5)

    def step5(out_file, state):
        args = ["-ss", state["start"], "-to", state["end"]]
        if is_video:
            args.extend(["-c", "copy"])
        return FfmpegProgressScreen(state["in_file"], out_file, args)

    return FilePickerScreen("Select Media File/Folder:", "", {}, step2)


def build_gallery_dl_flow():
    def step2(url, state):
        state["url"] = url
        return FilePickerScreen(
            "Save gallery to (directory):", os.path.expanduser("~/Downloads"), state, step3
        )

    def step3(path, state):
        expanded = abspath(path)
        backend = cast(GalleryDlBackend, get_backend("gallery-dl"))
        cmd = backend.build_command(state["url"], expanded)
        return GenericCliProgressScreen(cmd, "gallery-dl", expanded)

    return TextInputScreen("Enter gallery URL:", "https://...", "", {}, step2)


def file_in_out_flow(
    *,
    input_prompt: str,
    save_prompt: str,
    save_suffix: str,
    action_args,
    target_ext=None,
    progress_cls=FfmpegProgressScreen,
    param_prompt: str = None,
    param_placeholder: str = "",
    param_default: str = "",
    param_key: str = "param",
    param_validator=lambda v: v,
):
    """Wizard: input file → [param input] → save picker → progress screen.

    Covers the common "input → optional TextInput parameter → save picker →
    progress" pattern shared by ~16 workflows. For flows with OptionSelect
    or multi-step wizards, write the builder directly.

    save_suffix may include {ext} which is replaced with the input file's
    extension (e.g. "_muted{ext}" → "_muted.mp4"). Suffixes without {ext}
    are used literally (e.g. "_audio.mp3").
    """

    def _step_save(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        args = action_args(state) if callable(action_args) else action_args
        return progress_cls(expanded_in, expanded_out, args, target_ext=target_ext)

    def _step_param(value, state):
        state[param_key] = param_validator(value)
        base = os.path.splitext(state["in_file"])[0]
        ext = os.path.splitext(state["in_file"])[1]
        return FilePickerScreen(
            save_prompt, f"{base}{save_suffix.format(ext=ext)}", state, _step_save
        )

    def _step_input(in_file, state):
        state["in_file"] = os.path.abspath(os.path.expanduser(in_file))
        if param_prompt:
            return TextInputScreen(
                param_prompt, param_placeholder, param_default, state, _step_param
            )
        base = os.path.splitext(state["in_file"])[0]
        ext = os.path.splitext(state["in_file"])[1]
        return FilePickerScreen(
            save_prompt, f"{base}{save_suffix.format(ext=ext)}", state, _step_save
        )

    return FilePickerScreen(input_prompt, "", {}, _step_input)


def file_file_in_out_flow(
    *,
    input_prompt: str,
    second_prompt: str,
    save_prompt: str,
    save_suffix: str,
    action_args,
    progress_cls=FfmpegProgressScreen,
    target_ext=None,
):
    """Wizard: input file → second file picker → save picker → progress.

    Covers the "two inputs, one output" pattern shared by add_watermark,
    add_audio_track, mix_audio, and burn_subtitles. State carries
    `in_file` (set first) and `second_file` (set second).

    `action_args` may be a list (constant) or a callable `state -> list`
    (computed at save time; can read both `state['in_file']` and
    `state['second_file']`).

    `save_suffix` follows the same {ext} substitution as `file_in_out_flow`.
    """

    def _step_save(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        args = action_args(state) if callable(action_args) else action_args
        return progress_cls(expanded_in, expanded_out, args, target_ext=target_ext)

    def _step_second(second, state):
        state["second_file"] = os.path.abspath(os.path.expanduser(second))
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen(
            save_prompt, f"{base}{save_suffix.format(ext=ext)}", state, _step_save
        )

    def _step_input(in_file, state):
        state["in_file"] = os.path.abspath(os.path.expanduser(in_file))
        return FilePickerScreen(second_prompt, "", state, _step_second)

    return FilePickerScreen(input_prompt, "", {}, _step_input)


def file_file_progress_flow(
    *,
    input_prompt: str,
    second_prompt: str,
    cmd_builder,
    tool_name: str,
):
    """Wizard: input file → second file picker → GenericCliProgressScreen.

    For two-input operations that run in-place (no save picker). The
    `cmd_builder(state)` callable returns the full argv list to execute.

    State carries `in_file` and `second_file`.
    """

    def _step_second(second, state):
        state["second_file"] = os.path.abspath(os.path.expanduser(second))
        cmd = cmd_builder(state)
        target = state["second_file"]
        return GenericCliProgressScreen(cmd, tool_name, target)

    def _step_input(in_file, state):
        state["in_file"] = os.path.abspath(os.path.expanduser(in_file))
        return FilePickerScreen(second_prompt, "", state, _step_second)

    return FilePickerScreen(input_prompt, "", {}, _step_input)
