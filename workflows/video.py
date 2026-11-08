import os

from config import _load_full_config, validate_decimal, validate_resolution
from ui.progress import FfmpegProgressScreen
from ui.screens import FilePickerScreen, OptionSelectScreen, TextInputScreen
from workflows.shared import file_file_in_out_flow, file_in_out_flow
from workflows.utils import probe_first_subtitle_codec, subtitle_ext_for_codec


_CODEC_FORMATS = ["mp4", "mkv", "avi", "webm", "mov"]
_CODEC_CHOICES_BASE = ["libx264", "libx265", "libsvtav1", "copy"]
_HW_CODEC_LABELS = {
    "nvenc": "h264_nvenc (NVIDIA NVENC)",
    "vaapi": "h264_vaapi (Linux VA-API)",
    "videotoolbox": "h264_videotoolbox (macOS)",
    "qsv": "h264_qsv (Intel QuickSync)",
}
_X26X_PRESETS = [
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]
_SVT_AV1_PRESETS = ["0", "4", "6", "8", "10", "12"]


def _codec_choices() -> list[str]:
    """Return the list of codec picker choices for the wizard.

    Adds a hardware-accelerated option when `hw_accel` is set in config.
    Default config has empty `hw_accel` (no HW options listed).
    """
    choices = list(_CODEC_CHOICES_BASE)
    hw = _load_full_config().get("hw_accel", "")
    if hw in _HW_CODEC_LABELS:
        choices.insert(-1, _HW_CODEC_LABELS[hw])
    return choices


def _resolve_encoder(choice: str) -> str:
    """Map a wizard choice (e.g. 'h264_nvenc (NVIDIA NVENC)') to the ffmpeg encoder name.

    Hardware encoder labels and the software `libx*` names both pass through; unknowns
    return the choice string verbatim so a future preset survives unchanged.
    """
    for _key, label in _HW_CODEC_LABELS.items():
        if choice == label:
            return label.split(" ", 1)[0]  # e.g. "h264_nvenc (NVIDIA NVENC)" → "h264_nvenc"
    return choice


def _burn_subs_filter_arg(sub_path: str) -> str:
    expanded = os.path.abspath(os.path.expanduser(sub_path))
    res = []
    for ch in expanded:
        if ch == "\\":
            res.append("\\\\\\\\")
        elif ch == "'":
            res.append("\\\\\\'")
        elif ch == ":":
            res.append("\\\\:")
        elif ch in (",", "[", "]", ";", " ", "\"", "="):
            res.append("\\" + ch)
        else:
            res.append(ch)
    return f"subtitles=filename={''.join(res)}:si=0"


def build_burn_subtitles_flow():
    return file_file_in_out_flow(
        input_prompt="Select Video File:",
        second_prompt="Select Subtitle File (.srt/.ass):",
        save_prompt="Save Video As:",
        save_suffix="_hardsub.mp4",
        action_args=lambda s: ["-vf", _burn_subs_filter_arg(s["second_file"]), "-c:a", "copy"],
    )


def build_silence_remove_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_nosilence{ext}",
        action_args=[
            "-af",
            "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-30dB",
        ],
    )


def build_audio_visualizer_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File:",
        save_prompt="Save Waveform PNG As:",
        save_suffix="_waveform.png",
        action_args=[
            "-filter_complex",
            "showwaves=s=1920x240:mode=cline:colors=white",
            "-frames:v",
            "1",
        ],
        target_ext="png",
        progress_cls=FfmpegProgressScreen,
    )


def build_advanced_convert_video_flow():

    def step2(in_file, state):
        state["in_file"] = in_file
        return OptionSelectScreen("Target format:", _CODEC_FORMATS, state, step3)

    def step3(fmt, state):
        state["fmt"] = fmt
        return OptionSelectScreen("Codec:", _codec_choices(), state, step4)

    def step4(codec, state):
        state["codec"] = codec
        if codec == "copy":
            return _step_save_picker(state)
        if (
            codec in ("libx264", "libx265")
            or codec.startswith("h264_")
            or codec.startswith("hevc_")
        ):
            return OptionSelectScreen(
                f"{codec} preset (medium = default):",
                _X26X_PRESETS,
                state,
                _preset_then_save,
            )
        if codec == "libsvtav1":
            return OptionSelectScreen(
                "SVT-AV1 preset (lower = slower/better, 6 = default):",
                _SVT_AV1_PRESETS,
                state,
                _preset_then_save,
            )
        return _step_save_picker(state)

    def _preset_then_save(preset, state):
        state["preset"] = preset
        return _step_save_picker(state)

    def _step_save_picker(state):
        base, _ = os.path.splitext(state["in_file"])
        target_ext = state.get("fmt", "mp4")
        return FilePickerScreen(
            "Save As (or batch dir):",
            f"{base}_converted.{target_ext}",
            state,
            _step_save,
        )

    def _step_save(out_file, state):
        chosen = state.get("codec", "libx264")
        if chosen == "copy":
            args = ["-c", "copy"]
        else:
            encoder = _resolve_encoder(chosen)
            preset = state.get("preset", "medium")
            if encoder in ("h264_vaapi", "hevc_vaapi"):
                args = [
                    "-vaapi_device",
                    "/dev/dri/renderD128",
                    "-vf",
                    "format=nv12,hwupload",
                    "-c:v",
                    encoder,
                ]
            elif encoder in ("h264_qsv", "hevc_qsv"):
                args = ["-c:v", encoder, "-global_quality", "25"]
            elif encoder in ("h264_videotoolbox", "hevc_videotoolbox"):
                args = ["-c:v", encoder, "-q:v", "50"]
            else:
                args = ["-c:v", encoder, "-preset", preset]
        return FfmpegProgressScreen(
            state["in_file"],
            out_file,
            args,
            target_ext=state.get("fmt", "mp4"),
        )

    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)


def build_extract_audio_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save Audio As (or batch dir):",
        save_suffix="_audio.mp3",
        action_args=["-vn", "-acodec", "libmp3lame"],
        target_ext="mp3",
    )


def build_mute_video_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_muted{ext}",
        action_args=["-c:v", "copy", "-an"],
    )


def build_create_gif_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save GIF As (or batch dir):",
        save_suffix=".gif",
        action_args=["-vf", "fps=10,scale=320:-1:flags=lanczos"],
        target_ext="gif",
    )


def build_extract_frames_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen(
            "Frames Per Second:", "e.g. 1 (1 frame every sec)", "1", state, step3
        )

    def step3(fps, state):
        state["fps"] = validate_decimal(fps)
        base = os.path.splitext(state["in_file"])[0]
        return FilePickerScreen("Output Pattern:", f"{base}_%03d.png", state, step4)

    def step4(out_pattern, state):
        return FfmpegProgressScreen(state["in_file"], out_pattern, ["-vf", f"fps={state['fps']}"])

    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)


def build_video_speed_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = [
            "0.5x (Slow)",
            "0.75x (Slower)",
            "1.25x (Faster)",
            "1.5x (Fast)",
            "2.0x (Double Speed)",
        ]
        return OptionSelectScreen("Select Speed Multiplier:", opts, state, step3)

    def step3(speed_opt, state):
        val = speed_opt.split("x")[0]
        state["speed"] = float(val)
        state["v_pts"] = 1.0 / state["speed"]
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{val}x{ext}", state, step4)

    def step4(out_file, state):
        args = [
            "-filter_complex",
            f"[0:v]setpts={state['v_pts']}*PTS[v];[0:a]atempo={state['speed']}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
        return FfmpegProgressScreen(state["in_file"], out_file, args)

    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)


def build_rotate_video_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = ["90 Clockwise", "90 Counter-Clockwise", "180"]
        return OptionSelectScreen("Select Rotation:", opts, state, step3)

    def step3(rot_opt, state):
        if "Counter" in rot_opt:
            vf = "transpose=2"
        elif "180" in rot_opt:
            vf = "transpose=2,transpose=2"
        else:
            vf = "transpose=1"
        state["vf"] = vf
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_rotated{ext}", state, step4)

    def step4(out_file, state):
        return FfmpegProgressScreen(state["in_file"], out_file, ["-vf", state["vf"]])

    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)


def build_reverse_video_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_reversed{ext}",
        action_args=["-vf", "reverse", "-af", "areverse"],
    )


def build_add_watermark_flow():
    return file_file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        second_prompt="Select Watermark Image:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_watermarked{ext}",
        action_args=lambda s: [
            "-i",
            s["second_file"],
            "-filter_complex",
            "overlay=W-w-10:H-h-10",
        ],
    )


def build_add_audio_track_flow():
    return file_file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        second_prompt="Select Audio Track:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_mixed{ext}",
        action_args=lambda s: [
            "-i",
            s["second_file"],
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
        ],
    )


def build_scale_video_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_scaled{ext}",
        action_args=lambda s: ["-vf", f"scale={s['res']}"],
        param_prompt="Resolution (e.g. 1920:1080 or 1280:-1):",
        param_placeholder="1280:-1",
        param_default="1280:-1",
        param_key="res",
        param_validator=validate_resolution,
    )


def build_fade_video_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_fade{ext}",
        action_args=lambda s: ["-vf", f"fade=t=in:st=0:d={s['dur']}"],
        param_prompt="Fade In Duration (seconds):",
        param_placeholder="2",
        param_default="2",
        param_key="dur",
        param_validator=validate_decimal,
    )


def build_extract_subs_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        expanded = os.path.abspath(os.path.expanduser(in_file))
        codec = probe_first_subtitle_codec(expanded)
        ext = subtitle_ext_for_codec(codec)
        state["ext"] = ext
        base, _ = os.path.splitext(in_file)
        return FilePickerScreen("Save Subtitles As:", f"{base}.{ext}", state, step3)

    def step3(out_file, state):
        return FfmpegProgressScreen(
            state["in_file"],
            out_file,
            ["-map", "0:s:0", "-c:s", "copy"],
            target_ext=state.get("ext", "srt"),
        )

    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)
