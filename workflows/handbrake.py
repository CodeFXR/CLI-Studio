import os
from ui.screens import FilePickerScreen, OptionSelectScreen
from ui.progress import GenericCliProgressScreen
from workflows.utils import file_arg


_HANDBRAKE_PRESETS = [
    "Apple 1080p",
    "Apple 720p",
    "iPad 1080p",
    "Android Tablet 1080p",
    "Android Phone 1080p",
    "Chromecast 1080p",
    "Chromecast 720p",
    "Fire TV 1080p",
    "Roku 1080p",
    "Fast 1080p30",
    "HQ 1080p30 Surround",
    "Super HQ 1080p30 Surround",
    "Vimeo YouTube HQ 1080p",
    "Vimeo YouTube HQ 720p",
    "General Fast 1080p30",
    "General Very Fast 1080p30",
]


def build_handbrake_preset_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return OptionSelectScreen("HandBrake Device Preset:", _HANDBRAKE_PRESETS, state, step3)

    def step3(preset, state):
        state["preset"] = preset
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen(
            "Save As:",
            f"{base}_hb{ext if ext.lower() in ('.mp4', '.m4v', '.mkv') else '.mp4'}",
            state,
            step4,
        )

    def step4(out_file, state):
        expanded_in = file_arg(state["in_file"])
        expanded_out = file_arg(out_file)
        cmd = [
            "HandBrakeCLI",
            "-i",
            expanded_in,
            "-o",
            expanded_out,
            "--preset",
            state["preset"],
        ]
        return GenericCliProgressScreen(cmd, "HandBrakeCLI", expanded_out)

    return FilePickerScreen("Select Video File:", "", {}, step2)


def build_handbrake_list_presets_flow():
    """List all HandBrakeCLI presets available on the system.

    Output: one preset name per line in a .txt file (HandBrakeCLI's plain output).
    Useful before running the transcode flow to see what's installed.
    """

    def step2(out_file, state):
        expanded_out = file_arg(out_file)
        cmd = ["HandBrakeCLI", "--preset-list", "--no-dvdnav"]
        return GenericCliProgressScreen(cmd, "HandBrakeCLI", expanded_out, out_file=expanded_out)

    return FilePickerScreen(
        "Save preset list As (.txt):", f"{os.path.expanduser('~')}/handbrake_presets.txt", {}, step2
    )
