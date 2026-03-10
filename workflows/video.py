import os
from ui.screens import TextInputScreen, FilePickerScreen, OptionSelectScreen
from ui.progress import FfmpegProgressScreen

def build_extract_audio_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save Audio As (or batch dir):", f"{base}_audio.mp3", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vn", "-acodec", "libmp3lame"], target_ext="mp3")
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_mute_video_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_muted{ext}", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-c:v", "copy", "-an"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_create_gif_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save GIF As (or batch dir):", f"{base}.gif", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vf", "fps=10,scale=320:-1:flags=lanczos"], target_ext="gif")
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_extract_frames_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Frames Per Second:", "e.g. 1 (1 frame every sec)", "1", state, step3)
    def step3(fps, state):
        state['fps'] = fps
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Output Pattern:", f"{base}_%03d.png", state, step4)
    def step4(out_pattern, state):
        return FfmpegProgressScreen(state['in_file'], out_pattern, ["-vf", f"fps={state['fps']}"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_video_speed_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["0.5x (Slow)", "0.75x (Slower)", "1.25x (Faster)", "1.5x (Fast)", "2.0x (Double Speed)"]
        return OptionSelectScreen("Select Speed Multiplier:", opts, state, step3)
    def step3(speed_opt, state):
        val = speed_opt.split('x')[0]
        state['speed'] = float(val)
        state['v_pts'] = 1.0 / state['speed']
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{val}x{ext}", state, step4)
    def step4(out_file, state):
        args = ["-filter_complex", f"[0:v]setpts={state['v_pts']}*PTS[v];[0:a]atempo={state['speed']}[a]", "-map", "[v]", "-map", "[a]"]
        return FfmpegProgressScreen(state['in_file'], out_file, args)
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_rotate_video_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["90 Clockwise", "90 Counter-Clockwise", "180"]
        return OptionSelectScreen("Select Rotation:", opts, state, step3)
    def step3(rot_opt, state):
        if "Counter" in rot_opt: vf = "transpose=2"
        elif "180" in rot_opt: vf = "transpose=2,transpose=2"
        else: vf = "transpose=1"
        state['vf'] = vf
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_rotated{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vf", state['vf']])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_reverse_video_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_reversed{ext}", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vf", "reverse", "-af", "areverse"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_add_watermark_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return FilePickerScreen("Select Watermark Image:", "", state, step3)
    def step3(wm_file, state):
        state['wm_file'] = wm_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_watermarked{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-i", state['wm_file'], "-filter_complex", "overlay=W-w-10:H-h-10"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_add_audio_track_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return FilePickerScreen("Select Audio Track:", "", state, step3)
    def step3(audio_file, state):
        state['audio_file'] = audio_file
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_mixed{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-i", state['audio_file'], "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_scale_video_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Resolution (e.g. 1920:1080 or 1280:-1):", "1280:-1", "1280:-1", state, step3)
    def step3(res, state):
        state['res'] = res
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_scaled{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vf", f"scale={state['res']}"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_fade_video_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Fade In Duration (seconds):", "2", "2", state, step3)
    def step3(dur, state):
        state['dur'] = dur
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_fade{ext}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-vf", f"fade=t=in:st=0:d={state['dur']}"])
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)

def build_extract_subs_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save Subtitles As:", f"{base}.srt", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, ["-map", "0:s:0"], target_ext="srt")
    return FilePickerScreen("Select Video File/Folder:", "", {}, step2)