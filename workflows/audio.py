import os

from config import validate_decimal
from ui.progress import FfmpegProgressScreen, GenericCliProgressScreen
from ui.screens import FilePickerScreen, OptionSelectScreen
from workflows.shared import file_file_in_out_flow, file_in_out_flow


def build_change_volume_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_vol{ext}",
        action_args=lambda s: ["-filter:a", f"volume={s['vol']}"],
        param_prompt="Volume Multiplier:",
        param_placeholder="e.g. 2.0 (200%) or 0.5 (50%)",
        param_default="2.0",
        param_key="vol",
        param_validator=lambda v: validate_decimal(v, min_val=0.01, max_val=100.0),
    )


def build_audio_speed_flow():
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
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{val}x{ext}", state, step4)

    def step4(out_file, state):
        return FfmpegProgressScreen(
            state["in_file"], out_file, ["-filter:a", f"atempo={state['speed']}"]
        )

    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)


def build_reverse_audio_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_reversed{ext}",
        action_args=["-af", "areverse"],
    )


def build_normalize_audio_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_norm{ext}",
        action_args=["-af", "loudnorm"],
    )


def build_fade_audio_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_fade{ext}",
        action_args=lambda s: ["-af", f"afade=t=in:ss=0:d={s['dur']}"],
        param_prompt="Fade In Duration (seconds):",
        param_placeholder="3",
        param_default="3",
        param_key="dur",
        param_validator=lambda v: validate_decimal(v, min_val=0.1, max_val=86400.0),
    )


def build_mix_audio_flow():
    return file_file_in_out_flow(
        input_prompt="Select Primary Audio File/Folder:",
        second_prompt="Select Second Audio Track:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_mixed{ext}",
        action_args=lambda s: [
            "-i",
            s["second_file"],
            "-filter_complex",
            "amix=inputs=2:duration=longest",
        ],
    )


def build_ffmpeg_normalize_flow():
    """Two-pass loudness normalization via `ffmpeg-normalize` (the Python wrapper).

    Default target: -23 LUFS (broadcast standard). Replaces the single-pass
    `loudnorm` filter used by `normalize audio` with proper two-pass analysis.
    """

    def step2(in_file, state):
        state["in_file"] = in_file
        base, ext = os.path.splitext(in_file)
        return FilePickerScreen("Save Normalized Audio As:", f"{base}_norm{ext}", state, step3)

    def step3(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        ext_lower = os.path.splitext(expanded_out)[1].lower()
        codec_map = {
            ".mp3": "libmp3lame",
            ".m4a": "aac",
            ".aac": "aac",
            ".ogg": "libvorbis",
            ".opus": "libopus",
            ".flac": "flac",
            ".wav": "pcm_s16le",
            ".aif": "pcm_s16be",
            ".aiff": "pcm_s16be",
        }
        audio_codec = codec_map.get(ext_lower, "aac")
        cmd = [
            "ffmpeg-normalize",
            expanded_in,
            "-o",
            expanded_out,
            "-c:a",
            audio_codec,
            "-t",
            "-23",
            "-lrt",
            "11",
            "-tp",
            "-1.0",
        ]
        return GenericCliProgressScreen(cmd, "ffmpeg-normalize", expanded_out)

    return FilePickerScreen("Select Audio File:", "", {}, step2)
