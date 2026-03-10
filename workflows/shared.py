import os
from ui.screens import TextInputScreen, FilePickerScreen, OptionSelectScreen
from workflows.utils import get_media_duration
from ui.progress import DownloadProgressScreen, FfmpegProgressScreen

def build_download_flow(is_audio: bool, is_playlist: bool = False):
    def step2(url, state):
        state['url'] = url
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        return FilePickerScreen("Where to save?", default_path, state, step3)
    def step3(path, state):
        return DownloadProgressScreen(state['url'], path, is_audio=is_audio, is_playlist=is_playlist)
    title = "Enter Playlist URL:" if is_playlist else "Enter URL:"
    return TextInputScreen(title, "Right-click or Ctrl+Shift+V to Paste...", "", {}, step2)

def build_convert_media_flow(is_audio: bool):
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["mp3", "wav", "flac", "aac", "ogg"] if is_audio else ["mp4", "mkv", "avi", "webm", "mov"]
        return OptionSelectScreen("Select Target Format:", opts, state, step3)
    def step3(fmt, state):
        state['fmt'] = fmt
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save As (or select dir for batch):", f"{base}_converted.{fmt}", state, step4)
    def step4(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, [], target_ext=state['fmt'])
    return FilePickerScreen("Select Media File/Folder:", "", {}, step2)

def build_trim_media_flow(is_video: bool):
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Start Time:", "e.g. 00:01:30 or 90", "00:00:00", state, step3)
    def step3(start, state):
        state['start'] = start
        end_time = get_media_duration(state["in_file"])
        return TextInputScreen("End Time:", "e.g. 00:02:45 or 165", end_time, state, step4)
    def step4(end, state):
        state['end'] = end
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_trimmed{ext}", state, step5)
    def step5(out_file, state):
        args = ["-ss", state['start'], "-to", state['end']]
        if is_video: args.extend(["-c", "copy"])
        return FfmpegProgressScreen(state['in_file'], out_file, args)
    return FilePickerScreen("Select Media File/Folder:", "", {}, step2)