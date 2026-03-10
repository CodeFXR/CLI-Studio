import os
from ui.screens import TextInputScreen, FilePickerScreen, OptionSelectScreen
from ui.progress import FfmpegProgressScreen

def build_change_volume_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Volume Multiplier:", "e.g. 2.0 (200%) or 0.5 (50%)", "2.0", state, step3)
    def step3(vol, state):
        state['vol'] = vol
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_vol{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-filter:a", f"volume={state['vol']}"])
    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)

def build_audio_speed_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["0.5x (Slow)", "0.75x (Slower)", "1.25x (Faster)", "1.5x (Fast)", "2.0x (Double Speed)"]
        return OptionSelectScreen("Select Speed Multiplier:", opts, state, step3)
    def step3(speed_opt, state):
        val = speed_opt.split('x')[0]
        state['speed'] = float(val)
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{val}x{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-filter:a", f"atempo={state['speed']}"])
    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)

def build_reverse_audio_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_reversed{ext}", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-af", "areverse"])
    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)

def build_normalize_audio_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_norm{ext}", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-af", "loudnorm"])
    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)

def build_fade_audio_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Fade In Duration (seconds):", "3", "3", state, step3)
    def step3(dur, state):
        state['dur'] = dur
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_fade{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-af", f"afade=t=in:ss=0:d={state['dur']}"])
    return FilePickerScreen("Select Audio File/Folder:", "", {}, step2)

def build_mix_audio_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return FilePickerScreen("Select Second Audio Track:", "", state, step3)
    def step3(audio_file, state):
        state['audio_file'] = audio_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_mixed{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-i", state['audio_file'], "-filter_complex", "amix=inputs=2:duration=longest"])
    return FilePickerScreen("Select Primary Audio File/Folder:", "", {}, step2)