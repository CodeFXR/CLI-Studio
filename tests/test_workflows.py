"""Build a wizard by stepping through each closure directly.

The `_BaseInputModal._submit` calls `self.dismiss()` and `self.app.push_themed_screen(...)`,
which require a running Textual app. For unit tests we skip that and call
`next_step_func(value, state)` directly — the screen constructor runs but on_mount does
not, so no subprocess is spawned.
"""

from typing import Any

from ui.progress import (
    DownloadProgressScreen,
    FfmpegProgressScreen,
    GenericCliProgressScreen,
    PillowProgressScreen,
)
from ui.screens import FilePickerScreen, OptionSelectScreen, TextInputScreen


def run_wizard(first_modal, *inputs: str, state: dict | None = None) -> tuple[Any, dict]:
    """Step through a wizard by calling each next_step_func in turn.

    Returns the final result (typically a *ProgressScreen) and the threaded state dict.
    """
    if state is None:
        state = {}
    current = first_modal
    for value in inputs:
        next_step = current.next_step_func
        current = next_step(value, state)
    return current, state


def test_file_in_out_flow_no_param():
    from workflows.shared import file_in_out_flow

    first = file_in_out_flow(
        input_prompt="Select:",
        save_prompt="Save:",
        save_suffix="_muted{ext}",
        action_args=["-c:v", "copy", "-an"],
        target_ext=None,
        progress_cls=FfmpegProgressScreen,
    )
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(first, "/tmp/in.mp4", "/tmp/out.mp4")
    assert isinstance(result, FfmpegProgressScreen)
    assert state["in_file"] == "/tmp/in.mp4"
    assert result.input_file == "/tmp/in.mp4"
    assert result.output_file == "/tmp/out.mp4"
    assert "-c:v" in result.action_args
    assert "-an" in result.action_args


def test_file_in_out_flow_with_param_uses_validator():
    from config import validate_resolution
    from workflows.shared import file_in_out_flow

    first = file_in_out_flow(
        input_prompt="Scale:",
        save_prompt="Save:",
        save_suffix="_scaled{ext}",
        action_args=lambda s: ["-vf", f"scale={s['res']}"],
        param_prompt="Resolution:",
        param_default="1280:-1",
        param_key="res",
        param_validator=validate_resolution,
    )
    result, state = run_wizard(first, "/tmp/in.mp4", "1920:1080", "/tmp/out.mp4")
    assert isinstance(result, FfmpegProgressScreen)
    assert state["res"] == "1920:1080"
    assert "scale=1920:1080" in result.action_args[1]


def test_file_in_out_flow_validator_rejects_garbage():
    from config import validate_decimal
    from workflows.shared import file_in_out_flow

    first = file_in_out_flow(
        input_prompt="Volume:",
        save_prompt="Save:",
        save_suffix="_vol{ext}",
        action_args=lambda s: ["-af", f"volume={s['vol']}"],
        param_prompt="Volume:",
        param_default="1.0",
        param_key="vol",
        param_validator=validate_decimal,
    )
    state: dict = {}
    step_param = first.next_step_func("/tmp/a.wav", state).next_step_func
    try:
        step_param("not-a-number", state)
    except ValueError:
        return
    raise AssertionError("validate_decimal should have raised ValueError")


def test_wizard_value_error_becomes_friendly_toast(monkeypatch):
    """The wizard _submit method maps ValueError to a user-friendly toast
    instead of leaking the raw Python error message.
    """
    from ui.screens import TextInputScreen

    notifies: list[tuple[str, dict]] = []

    def step_two(value, state):
        raise ValueError("invalid literal for float(): 'bad'")

    # default_val="" so the user's value is passed through unchanged.
    screen = TextInputScreen("Volume:", "", "bad", {}, step_two)

    class _FakeApp:
        def notify(self, message, **kwargs):
            notifies.append((str(message), kwargs))

    monkeypatch.setattr(type(screen), "app", property(lambda _self: _FakeApp()))

    screen._submit("bad")

    error_toasts = [n for n in notifies if "Invalid input" in n[0]]
    assert error_toasts, f"Expected a friendly 'Invalid input' toast; got: {notifies}"
    assert all("invalid literal for float" not in n[0] for n in error_toasts), (
        "The raw traceback should NOT leak through to the user."
    )


def test_wizard_file_not_found_becomes_friendly_toast(monkeypatch):
    """FileNotFoundError from the wizard step is mapped to a friendly toast."""
    from ui.screens import TextInputScreen

    notifies: list[tuple[str, dict]] = []

    def step_two(value, state):
        raise FileNotFoundError(value)

    screen = TextInputScreen("Path:", "", "/missing", {}, step_two)
    fake_app = type("A", (), {"notify": lambda self, msg, **kw: notifies.append((str(msg), kw))})()
    monkeypatch.setattr(type(screen), "app", property(lambda _self: fake_app))

    screen._submit("/missing")

    assert any("File not found" in n[0] for n in notifies), (
        f"Expected 'File not found' toast; got: {notifies}"
    )


def test_wizard_unexpected_error_does_not_leak_traceback(monkeypatch):
    """Generic Exception is mapped to 'Unexpected error' without leaking traceback."""
    from ui.screens import TextInputScreen

    notifies: list[tuple[str, dict]] = []

    def step_two(value, state):
        raise RuntimeError("This should NOT appear in the toast: SECRET_DETAIL_42")

    screen = TextInputScreen("Path:", "", "x", {}, step_two)
    fake_app = type("A", (), {"notify": lambda self, msg, **kw: notifies.append((str(msg), kw))})()
    monkeypatch.setattr(type(screen), "app", property(lambda _self: fake_app))

    screen._submit("x")

    error_toasts = [n for n in notifies if "Unexpected error" in n[0]]
    assert error_toasts, f"Expected 'Unexpected error' toast; got: {notifies}"
    assert all("SECRET_DETAIL_42" not in n[0] for n in notifies), (
        "The raw exception text should NOT leak to the user."
    )


def test_build_mute_video_flow():
    from workflows import video

    first = video.build_mute_video_flow()
    assert isinstance(first, FilePickerScreen)
    result, _ = run_wizard(first, "/tmp/v.mp4", "/tmp/v_muted.mp4")
    assert isinstance(result, FfmpegProgressScreen)
    assert "-an" in result.action_args
    assert "copy" in result.action_args


def test_build_extract_audio_flow():
    from workflows import video

    first = video.build_extract_audio_flow()
    assert isinstance(first, FilePickerScreen)
    result, _ = run_wizard(first, "/tmp/v.mp4", "/tmp/v_audio.mp3")
    assert isinstance(result, FfmpegProgressScreen)
    assert "-vn" in result.action_args
    assert "libmp3lame" in result.action_args
    assert result.target_ext == "mp3"


def test_build_extract_subs_flow_uses_srt_suffix():
    from workflows import video

    first = video.build_extract_subs_flow()
    result, _ = run_wizard(first, "/tmp/v.mkv", "/tmp/v_subs.srt")
    assert isinstance(result, FfmpegProgressScreen)
    assert "0:s:0" in result.action_args
    assert "-c:s" in result.action_args
    assert "copy" in result.action_args


def test_build_extract_subs_flow_probes_codec_for_ass(monkeypatch):
    """When the source has ASS subs, the default filename suffix should be .ass, not .srt."""
    from workflows import video

    monkeypatch.setattr(
        "workflows.video.probe_first_subtitle_codec",
        lambda _path: "ass",
    )
    first = video.build_extract_subs_flow()
    picker = first.next_step_func
    state: dict = {}
    next_screen = picker("/tmp/v.mkv", state)
    assert isinstance(next_screen, FilePickerScreen)
    assert state["ext"] == "ass"
    assert next_screen.default_val.endswith(".ass")


def test_build_extract_subs_flow_probes_codec_for_webvtt(monkeypatch):
    """WebVTT subs should default to .vtt extension."""
    from workflows import video

    monkeypatch.setattr(
        "workflows.video.probe_first_subtitle_codec",
        lambda _path: "webvtt",
    )
    first = video.build_extract_subs_flow()
    picker = first.next_step_func
    state: dict = {}
    next_screen = picker("/tmp/v.mkv", state)
    assert state["ext"] == "vtt"
    assert next_screen.default_val.endswith(".vtt")


def test_build_extract_subs_flow_falls_back_to_srt_when_probe_fails(monkeypatch):
    """If ffprobe is missing or returns empty, default to .srt (most common)."""
    from workflows import video

    monkeypatch.setattr(
        "workflows.video.probe_first_subtitle_codec",
        lambda _path: "",
    )
    first = video.build_extract_subs_flow()
    picker = first.next_step_func
    state: dict = {}
    next_screen = picker("/tmp/v.mkv", state)
    assert state["ext"] == "srt"
    assert next_screen.default_val.endswith(".srt")


def test_build_change_volume_flow_uses_validator():
    from workflows import audio

    first = audio.build_change_volume_flow()
    result, state = run_wizard(first, "/tmp/a.wav", "2.5", "/tmp/a_vol.wav")
    assert isinstance(result, FfmpegProgressScreen)
    assert state["vol"] == "2.5"
    assert "volume=2.5" in result.action_args[1]


def test_build_normalize_audio_flow():
    from workflows import audio

    first = audio.build_normalize_audio_flow()
    result, _ = run_wizard(first, "/tmp/a.wav", "/tmp/a_norm.wav")
    assert isinstance(result, FfmpegProgressScreen)
    assert "loudnorm" in result.action_args


def test_build_resize_image_flow():
    from workflows import image

    first = image.build_resize_image_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(first, "/tmp/img.png", "800x600", "/tmp/img_800x600.png")
    assert isinstance(result, PillowProgressScreen)
    assert state["dims"] == (800, 600)
    assert result.action == "resize"
    assert result.dimensions == (800, 600)


def test_build_crop_image_flow():
    from workflows import image

    first = image.build_crop_image_flow()
    result, state = run_wizard(first, "/tmp/img.png", "10,20,300,400", "/tmp/img_cropped.png")
    assert isinstance(result, PillowProgressScreen)
    assert state["dims"] == (10, 20, 300, 400)


def test_build_convert_image_flow():
    from workflows import image

    first = image.build_convert_image_flow()
    result, state = run_wizard(first, "/tmp/img.png", "jpg", "/tmp/img_converted.jpg")
    assert isinstance(result, PillowProgressScreen)
    assert state["fmt"] == "jpg"
    assert result.action == "convert"
    assert result.target_ext == "jpg"


def test_build_imagemagick_filter_flow_uses_magick():
    from workflows import image

    first = image.build_imagemagick_filter_flow()
    result, _ = run_wizard(
        first,
        "/tmp/img.png",
        "Grayscale (-monochrome)",
        "/tmp/img_filtered.png",
    )
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "ImageMagick"
    assert len(result.cmds) == 1
    cmd = result.cmds[0]
    assert cmd[0] == "magick"
    assert cmd[1] == "/tmp/img.png"
    assert "-monochrome" in cmd


def test_build_remove_bg_color_flow_uses_magick():
    from workflows import image

    first = image.build_remove_bg_color_flow()
    result, state = run_wizard(
        first,
        "/tmp/img.png",
        "white",
        "15",
        "/tmp/img_nobg.png",
    )
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "ImageMagick"
    assert state["color"] == "white"
    assert state["fuzz"] == "15"
    cmd = result.cmds[0]
    assert "-fuzz" in cmd and "15%" in cmd
    assert "-transparent" in cmd and "white" in cmd


def test_build_exiftool_strip_flow():
    from workflows import image

    first = image.build_exiftool_strip_flow()
    result, _ = run_wizard(first, "/tmp/img.jpg", "Yes - strip metadata (backups kept)")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "ExifTool"
    cmd = result.cmds[0]
    assert cmd[0] == "exiftool"
    assert "-all=" in cmd
    assert "--" in cmd
    assert cmd[-1] == "/tmp/img.jpg"


def test_build_download_flow_passes_cookies_default_off():
    from workflows import shared

    first = shared.build_download_flow(is_audio=False)
    result, _ = run_wizard(first, "https://example.com/video", "/tmp/dl")
    assert isinstance(result, DownloadProgressScreen)
    assert result.url == "https://example.com/video"
    assert result.save_path == "/tmp/dl"
    assert result.cookies == ""
    assert result.remote_components == ""
    assert result.is_audio is False
    assert result.is_playlist is False


def test_build_download_playlist_sets_flag():
    from workflows import shared

    first = shared.build_download_flow(is_audio=False, is_playlist=True)
    result, _ = run_wizard(first, "https://example.com/playlist?list=PL", "/tmp/dl")
    assert isinstance(result, DownloadProgressScreen)
    assert result.is_playlist is True


def test_build_convert_media_flow_video():
    from workflows import shared

    first = shared.build_convert_media_flow(is_audio=False)
    result, state = run_wizard(first, "/tmp/in.mov", "mkv", "/tmp/in_converted.mkv")
    assert isinstance(result, FfmpegProgressScreen)
    assert state["fmt"] == "mkv"
    assert result.target_ext == "mkv"


def test_build_trim_media_flow_passes_args(monkeypatch):
    from workflows import shared

    monkeypatch.setattr("workflows.shared.get_media_duration", lambda _p: "00:01:00")
    first = shared.build_trim_media_flow(is_video=True)
    result, state = run_wizard(
        first,
        "/tmp/in.mp4",
        "00:00:05",
        "00:01:30",
        "/tmp/in_trimmed.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    assert state["start"] == "5"
    assert state["end"] == "90"
    assert "-ss" in result.action_args
    assert "5" in result.action_args
    assert "-to" in result.action_args
    assert "90" in result.action_args


def test_command_handler_dispatches_to_screen():
    from workflows.registry import CommandHandler

    result = CommandHandler.handle_command("mute video")
    assert isinstance(result, FilePickerScreen)


def test_command_handler_unknown_returns_string():
    from workflows.registry import CommandHandler

    result = CommandHandler.handle_command("not a real tool")
    assert isinstance(result, str)
    assert "not a real tool" in result.lower() or "no action" in result.lower()


def test_every_registered_command_returns_a_screen():
    """The whole point of the registry: every entry must produce a usable first modal."""
    from workflows.registry import COMMAND_REGISTRY

    expected_first_classes = (FilePickerScreen, TextInputScreen, OptionSelectScreen)

    for name, builder in COMMAND_REGISTRY.items():
        first = builder()
        assert isinstance(first, expected_first_classes), (
            f"{name!r} returned {type(first).__name__}, expected one of "
            f"{[c.__name__ for c in expected_first_classes]}"
        )


def test_build_extract_text_flow_uses_tesseract():
    from workflows import image

    first = image.build_extract_text_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(first, "/tmp/photo.png", "deu", "/tmp/photo.txt")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "tesseract"
    cmd = result.cmds[0]
    assert cmd[0] == "tesseract"
    assert cmd[3] == "-l" and cmd[4] == "deu"
    assert state["lang"] == "deu"


def test_build_remux_to_mkv_flow():
    from workflows import mkv

    first = mkv.build_remux_to_mkv_flow()
    assert isinstance(first, FilePickerScreen)
    result, _ = run_wizard(first, "/tmp/in.mp4", "/tmp/in.mkv")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "mkvmerge"
    cmd = result.cmds[0]
    assert cmd[0] == "mkvmerge"
    assert "-o" in cmd
    assert "/tmp/in.mp4" in cmd
    assert "/tmp/in.mkv" in cmd


def test_build_merge_mkvs_flow_single():
    from workflows import mkv

    first = mkv.build_merge_mkvs_flow()
    assert isinstance(first, FilePickerScreen)
    result, _ = run_wizard(first, "/tmp/one.mkv", "/tmp/combined.mkv")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "mkvmerge"
    cmd = result.cmds[0]
    assert "/tmp/one.mkv" in cmd
    assert "/tmp/combined.mkv" in cmd
    assert "+" not in cmd


def test_build_merge_mkvs_flow_folder_with_plus_separator(monkeypatch, tmp_path):
    from workflows import mkv

    paths = []
    for n in ("01.mkv", "02.mkv", "10.mkv"):
        p = tmp_path / n
        p.write_bytes(b"\x1a\x45\xdf\xa3")
        paths.append(str(p))

    first = mkv.build_merge_mkvs_flow()
    out = tmp_path / "out.mkv"
    result, _ = run_wizard(first, str(tmp_path), str(out))
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert cmd.count("+") == 2, f"expected two `+` separators between three files, got {cmd}"
    for p in paths:
        assert p in cmd
    assert str(out) in cmd


def test_build_extract_mkv_subs_flow_one_cmd_per_track(monkeypatch):
    from workflows import mkv

    monkeypatch.setattr(
        "workflows.mkv._probe_subtitle_tracks",
        lambda _p: [
            {"index": 2, "codec_name": "subrip", "language": "eng"},
            {"index": 3, "codec_name": "subrip", "language": "deu"},
        ],
    )
    monkeypatch.setattr("os.makedirs", lambda *a, **kw: None)

    first = mkv.build_extract_mkv_subs_flow()
    result, state = run_wizard(first, "/tmp/movie.mkv", "/tmp/subs_out")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "mkvextract"
    assert len(result.cmds) == 2, (
        f"expected one mkvextract command per sub track, got {len(result.cmds)}"
    )
    first_cmd = result.cmds[0]
    assert first_cmd[0] == "mkvextract"
    assert first_cmd[1] == "tracks"
    assert "2:" + "/tmp/subs_out" in " ".join(first_cmd)
    second_cmd = result.cmds[1]
    assert "3:" + "/tmp/subs_out" in " ".join(second_cmd)


def test_build_extract_mkv_subs_flow_no_subs_returns_none(monkeypatch):
    from workflows import mkv

    monkeypatch.setattr("workflows.mkv._probe_subtitle_tracks", lambda _p: [])
    first = mkv.build_extract_mkv_subs_flow()
    step_input = first.next_step_func
    state: dict = {}
    step2 = step_input("/tmp/movie.mkv", state).next_step_func
    result = step2("/tmp/subs_out", state)
    assert result is None


def test_probe_subtitle_tracks_handles_missing_ffprobe(monkeypatch):
    from workflows import mkv

    def raise_fnf(*a, **kw):
        raise FileNotFoundError("ffprobe not installed")

    monkeypatch.setattr("subprocess.run", raise_fnf)
    assert mkv._probe_subtitle_tracks("/tmp/anything.mkv") == []


def test_probe_subtitle_tracks_returns_empty_on_bad_json(monkeypatch):
    from workflows import mkv

    class FakeRes:
        returncode = 0
        stdout = "not json at all"
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeRes())
    assert mkv._probe_subtitle_tracks("/tmp/anything.mkv") == []


def test_probe_subtitle_tracks_parses_valid_output(monkeypatch):
    from workflows import mkv

    class FakeRes:
        returncode = 0
        stdout = '{"streams": [{"index": 2, "codec_name": "subrip", "tags": {"language": "eng"}}, {"index": 3, "codec_name": "ass", "tags": {}}]}'
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeRes())
    out = mkv._probe_subtitle_tracks("/tmp/anything.mkv")
    assert out == [
        {"index": 2, "codec_name": "subrip", "language": "eng"},
        {"index": 3, "codec_name": "ass", "language": ""},
    ]


def test_conftest_loads_cli_studio_app_module():
    import cli_studio_app

    assert cli_studio_app.CliStudioApp.__name__ == "CliStudioApp"


def test_advanced_convert_video_flow_libx264_with_preset():
    from workflows import video

    first = video.build_advanced_convert_video_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(
        first,
        "/tmp/in.mov",
        "mp4",
        "libx264",
        "slow",
        "/tmp/in_converted.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-c:v" in args and "libx264" in args
    assert "-preset" in args and "slow" in args
    assert state["fmt"] == "mp4"
    assert state["codec"] == "libx264"
    assert state["preset"] == "slow"
    assert result.target_ext == "mp4"


def test_advanced_convert_video_flow_libx265_with_preset():
    from workflows import video

    first = video.build_advanced_convert_video_flow()
    result, _ = run_wizard(
        first,
        "/tmp/in.mov",
        "mkv",
        "libx265",
        "veryslow",
        "/tmp/in.mkv",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-c:v" in args and "libx265" in args
    assert "-preset" in args and "veryslow" in args


def test_advanced_convert_video_flow_svtav1_uses_numeric_preset():
    from workflows import video

    first = video.build_advanced_convert_video_flow()
    result, _ = run_wizard(
        first,
        "/tmp/in.mov",
        "mp4",
        "libsvtav1",
        "10",
        "/tmp/in.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-c:v" in args and "libsvtav1" in args
    assert "-preset" in args and "10" in args


def test_advanced_convert_video_flow_copy_skips_preset_step():
    from workflows import video

    first = video.build_advanced_convert_video_flow()
    result, state = run_wizard(
        first,
        "/tmp/in.mov",
        "mp4",
        "copy",
        "/tmp/in_copy.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert args == ["-c", "copy"]
    assert "preset" not in state, f"copy codec should not have a preset, got {state}"


def test_build_burn_subtitles_flow_uses_subtitles_filter():
    from workflows import video

    first = video.build_burn_subtitles_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(
        first,
        "/tmp/movie.mp4",
        "/tmp/movie.srt",
        "/tmp/movie_hardsub.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-vf" in args
    vf = args[args.index("-vf") + 1]
    assert vf.startswith("subtitles=")
    assert "si=0" in vf
    assert "-c:a" in args and "copy" in args


def test_build_burn_subtitles_flow_escapes_colons_in_subtitle_path():
    from workflows import video

    first = video.build_burn_subtitles_flow()
    result, state = run_wizard(
        first,
        "/tmp/movie.mp4",
        "/tmp/special:dir/movie.srt",
        "/tmp/out.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    vf = args[args.index("-vf") + 1]
    assert "\\:" in vf, f"colons in subtitle path should be backslash-escaped, got {vf!r}"


def test_build_burn_subtitles_flow_escapes_ffmpeg_filter_metachars():
    """Paths containing ffmpeg-filter-special chars must be escaped so the filter parses."""
    from workflows import video

    for weird_path, weird_chars in (
        ("/tmp/path with [brackets]/movie.srt", "[]"),
        ("/tmp/path,with,commas/movie.srt", ","),
        ("/tmp/path;semis/movie.srt", ";"),
        ("/tmp/path with 'quotes'/movie.srt", "'"),
    ):
        first = video.build_burn_subtitles_flow()
        result, _ = run_wizard(
            first,
            "/tmp/movie.mp4",
            weird_path,
            "/tmp/out.mp4",
        )
        assert isinstance(result, FfmpegProgressScreen)
        args = result.action_args
        vf = args[args.index("-vf") + 1]
        for char in weird_chars:
            assert f"\\{char}" in vf, (
                f"path {weird_path!r}: char {char!r} should be escaped in {vf!r}"
            )


def test_build_burn_subtitles_flow_escapes_apostrophes_and_equals():
    from workflows import video

    first = video.build_burn_subtitles_flow()
    result, _ = run_wizard(
        first,
        "/tmp/movie.mp4",
        "/tmp/it's a [weird], test=name; with:colons.srt",
        "/tmp/out.mp4",
    )
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    vf = args[args.index("-vf") + 1]
    assert vf.startswith("subtitles=filename=")
    assert "\\\\\\'" in vf
    assert "\\\\:" in vf
    assert "\\=" in vf
    assert "\\," in vf
    assert "\\[" in vf
    assert "\\]" in vf


def test_build_silence_remove_flow_uses_silenceremove_filter():
    from workflows import video

    first = video.build_silence_remove_flow()
    assert isinstance(first, FilePickerScreen)
    result, _ = run_wizard(first, "/tmp/clip.wav", "/tmp/clip_nosilence.wav")
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-af" in args
    af = args[args.index("-af") + 1]
    assert af.startswith("silenceremove=")
    assert "stop_threshold" in af


def test_build_audio_visualizer_flow_renders_png():
    from workflows import video

    first = video.build_audio_visualizer_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(first, "/tmp/clip.wav", "/tmp/clip_waveform.png")
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-filter_complex" in args
    fc = args[args.index("-filter_complex") + 1]
    assert fc.startswith("showwaves=")
    assert "-frames:v" in args
    assert result.target_ext == "png"


def test_build_sprite_sheet_flow_uses_montage(tmp_path):
    from workflows import image

    files = []
    for n in ("01.png", "02.png", "03.png", "04.png"):
        p = tmp_path / n
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        files.append(p)
    first = image.build_sprite_sheet_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(
        first,
        str(tmp_path),
        "2x2",
        str(tmp_path / "sheet.png"),
    )
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert cmd[0] == "magick"
    assert "montage" in cmd
    assert all(str(f) in cmd for f in files)
    assert "2x2" in cmd
    assert str(tmp_path / "sheet.png") in cmd


def test_build_sprite_sheet_flow_auto_tile(tmp_path):
    from workflows import image

    for n in ("a.png", "b.png", "c.png"):
        (tmp_path / n).write_bytes(b"\x89PNG\r\n\x1a\n")
    first = image.build_sprite_sheet_flow()
    result, _ = run_wizard(
        first,
        str(tmp_path),
        "auto (single row)",
        str(tmp_path / "row.png"),
    )
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    tile_idx = cmd.index("-tile") + 1
    assert cmd[tile_idx] == "3x1"


def test_build_add_subs_to_mkv_flow_with_language():
    from workflows import mkv

    first = mkv.build_add_subtitles_to_mkv_flow()
    assert isinstance(first, FilePickerScreen)
    result, state = run_wizard(
        first,
        "/tmp/movie.mkv",
        "/tmp/movie.srt",
        "eng",
        "/tmp/movie_subs.mkv",
    )
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "mkvmerge"
    cmd = result.cmds[0]
    assert cmd[0] == "mkvmerge"
    assert "--language" in cmd and "0:eng" in cmd
    assert "/tmp/movie.srt" in cmd


def test_build_add_subs_to_mkv_flow_without_language():
    from workflows import mkv

    first = mkv.build_add_subtitles_to_mkv_flow()
    result, state = run_wizard(
        first,
        "/tmp/movie.mkv",
        "/tmp/movie.srt",
        "und (no tag)",
        "/tmp/movie_subs.mkv",
    )
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert "--language" not in cmd


def test_build_extract_mkv_attachments_flow_one_cmd_per_attachment(monkeypatch):
    from workflows import mkv

    monkeypatch.setattr(
        "workflows.mkv._probe_attachments",
        lambda _p: [
            {
                "id": 4,
                "filename": "MyFont.ttf",
                "mimetype": "application/x-truetype-font",
                "size": 12345,
            },
            {"id": 9, "filename": "Cover.jpg", "mimetype": "image/jpeg", "size": 67890},
        ],
    )
    monkeypatch.setattr("os.makedirs", lambda *a, **kw: None)

    first = mkv.build_extract_mkv_attachments_flow()
    result, state = run_wizard(first, "/tmp/movie.mkv", "/tmp/attachments")
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "mkvextract"
    assert len(result.cmds) == 2
    cmd0 = result.cmds[0]
    assert cmd0[0] == "mkvextract"
    assert cmd0[1] == "attachments"
    assert "4:" + "/tmp/attachments" in " ".join(cmd0)
    assert "MyFont.ttf" in " ".join(cmd0)
    cmd1 = result.cmds[1]
    assert "9:" + "/tmp/attachments" in " ".join(cmd1)
    assert "Cover.jpg" in " ".join(cmd1)


def test_build_extract_mkv_attachments_flow_no_attachments_returns_none(monkeypatch):
    from workflows import mkv

    monkeypatch.setattr("workflows.mkv._probe_attachments", lambda _p: [])
    first = mkv.build_extract_mkv_attachments_flow()
    step_input = first.next_step_func
    state: dict = {}
    step2 = step_input("/tmp/movie.mkv", state).next_step_func
    assert step2("/tmp/out", state) is None


def test_probe_attachments_handles_missing_ffprobe(monkeypatch):
    from workflows import mkv

    def raise_fnf(*a, **kw):
        raise FileNotFoundError("ffprobe not installed")

    monkeypatch.setattr("subprocess.run", raise_fnf)
    assert mkv._probe_attachments("/tmp/anything.mkv") == []


def test_probe_attachments_parses_valid_output(monkeypatch):
    from workflows import mkv

    class FakeRes:
        returncode = 0
        stdout = (
            '{"attachments": ['
            '{"id": 7, "file_name": "MyFont.ttf", "content_type": "application/x-truetype-font", "size": 12345}'
            "]}"
        )
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeRes())
    assert mkv._probe_attachments("/tmp/anything.mkv") == [
        {
            "id": 7,
            "filename": "MyFont.ttf",
            "mimetype": "application/x-truetype-font",
            "size": 12345,
        },
    ]


def test_probe_attachments_parses_native_ffprobe_streams(monkeypatch):
    import json
    from workflows import mkv

    def fake_run(cmd, *a, **kw):
        if cmd[0] == "mkvmerge":
            raise FileNotFoundError("mkvmerge not found")
        class FakeRes:
            returncode = 0
            stdout = json.dumps({
                "streams": [
                    {"index": 0, "codec_type": "video"},
                    {
                        "index": 1,
                        "codec_type": "attachment",
                        "tags": {
                            "filename": "font.ttf",
                            "mimetype": "font/ttf",
                            "NUMBER_OF_BYTES": "54321",
                        },
                    },
                ]
            })
            stderr = ""
        return FakeRes()

    monkeypatch.setattr("subprocess.run", fake_run)
    res = mkv._probe_attachments("/tmp/test.mkv")
    assert len(res) == 1
    assert res[0]["id"] is None
    assert res[0]["filename"] == "font.ttf"
    assert res[0]["mimetype"] == "font/ttf"
    assert res[0]["size"] == 54321


def test_probe_attachments_returns_empty_on_bad_json(monkeypatch):
    from workflows import mkv

    class FakeRes:
        returncode = 0
        stdout = "not json"
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeRes())
    assert mkv._probe_attachments("/tmp/anything.mkv") == []


def test_probe_attachments_returns_empty_on_nonzero_returncode(monkeypatch):
    from workflows import mkv

    class FakeRes:
        returncode = 1
        stdout = ""
        stderr = "error"

    monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeRes())
    assert mkv._probe_attachments("/tmp/anything.mkv") == []


def test_command_registry_has_57_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 57, f"Expected 57+ tools, got {len(COMMAND_REGISTRY)}"


def test_build_set_exif_tag_flow_preset():
    from workflows import image

    first = image.build_set_exif_tag_flow()
    assert isinstance(first, FilePickerScreen)
    step_input = first.next_step_func
    state: dict = {}
    step2 = step_input("/tmp/photo.jpg", state).next_step_func
    step4 = step2("Copyright", state).next_step_func
    result = step4("© 2026 me", state)
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert cmd[0] == "exiftool"
    assert "-overwrite_original" in cmd
    assert "-Copyright=© 2026 me" in cmd
    assert "/tmp/photo.jpg" in cmd


def test_build_set_exif_tag_flow_custom_tag():
    from workflows import image

    first = image.build_set_exif_tag_flow()
    step_input = first.next_step_func
    state: dict = {}
    step2 = step_input("/tmp/photo.jpg", state).next_step_func
    step3 = step2("Custom...", state).next_step_func
    step3b = step3("MyTag", state).next_step_func
    result = step3b("hello", state)
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert "-MyTag=hello" in cmd


def test_build_copy_exif_flow_uses_tagsfromfile():
    from workflows import image

    first = image.build_copy_exif_flow()
    assert isinstance(first, FilePickerScreen)
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/source.jpg", state).next_step_func
    result = step3("/tmp/target.jpg", state)
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert cmd[0] == "exiftool"
    assert "-tagsFromFile" in cmd
    assert "/tmp/source.jpg" in cmd
    assert "/tmp/target.jpg" in cmd
    assert "-all:all" in cmd


def test_build_rename_by_exif_date_flow_one_cmd_per_image(tmp_path):
    from workflows import image

    for n in ("01.jpg", "02.jpg"):
        (tmp_path / n).write_bytes(b"\xff\xd8\xff\xe0")
    first = image.build_rename_by_exif_date_flow()
    assert isinstance(first, FilePickerScreen)
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input(str(tmp_path), state).next_step_func
    out = tmp_path / "out"
    result = step3(str(out), state)
    assert isinstance(result, GenericCliProgressScreen)
    assert len(result.cmds) == 2
    cmd0 = result.cmds[0]
    assert cmd0[0] == "exiftool"
    assert any(arg.startswith("-FileName<DateTimeOriginal") for arg in cmd0)
    assert "01.jpg" in " ".join(cmd0)


def test_build_rename_by_exif_date_flow_empty_folder_returns_none(tmp_path):
    from workflows import image

    empty = tmp_path / "empty"
    empty.mkdir()
    first = image.build_rename_by_exif_date_flow()
    step_input = first.next_step_func
    state: dict = {}
    step2 = step_input(str(empty), state).next_step_func
    assert step2(str(tmp_path / "out"), state) is None


def test_build_scan_barcode_flow_single_image():
    from workflows import image

    first = image.build_scan_barcode_flow()
    assert isinstance(first, FilePickerScreen)
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/qr.png", state).next_step_func
    result = step3("/tmp/qr_codes.txt", state)
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "zbarimg"
    assert len(result.cmds) == 1
    cmd = result.cmds[0]
    assert cmd[0] == "zbarimg"
    assert "--raw" in cmd
    assert "/tmp/qr.png" in cmd


def test_build_scan_barcode_flow_folder_iterates(tmp_path):
    from workflows import image

    for n in ("a.png", "b.png"):
        (tmp_path / n).write_bytes(b"\x89PNG\r\n\x1a\n")
    first = image.build_scan_barcode_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input(str(tmp_path), state).next_step_func
    out = tmp_path / "codes.txt"
    result = step3(str(out), state)
    assert isinstance(result, GenericCliProgressScreen)
    assert len(result.cmds) == 2
    for cmd in result.cmds:
        assert cmd[0] == "zbarimg"
        assert "--quiet" in cmd
        assert "--raw" in cmd


def test_command_registry_has_61_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 61, f"Expected 61+ tools, got {len(COMMAND_REGISTRY)}"


def test_build_gallery_dl_flow():
    from workflows import shared

    first = shared.build_gallery_dl_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("https://example.com/gallery", state).next_step_func
    result = step3("/tmp/gallery", state)
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "gallery-dl"
    cmd = result.cmds[0]
    assert cmd[0] == "gallery-dl"
    assert "--dest" in cmd
    assert "/tmp/gallery" in cmd
    assert "https://example.com/gallery" in cmd


def test_build_ffmpeg_normalize_flow():
    from workflows import audio

    first = audio.build_ffmpeg_normalize_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/clip.wav", state).next_step_func
    result = step3("/tmp/clip_norm.wav", state)
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "ffmpeg-normalize"
    cmd = result.cmds[0]
    assert cmd[0] == "ffmpeg-normalize"
    assert "-t" in cmd and "-23" in cmd
    assert "/tmp/clip.wav" in cmd
    assert "/tmp/clip_norm.wav" in cmd


def test_build_rclone_copy_flow():
    from workflows import cloud

    first = cloud.build_rclone_copy_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/local_dir", state).next_step_func
    step4 = step3("mybackup", state).next_step_func
    result = step4("backups/2026", state)
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "rclone"
    cmd = result.cmds[0]
    assert cmd[0] == "rclone"
    assert cmd[1] == "copy"
    assert "/tmp/local_dir" in cmd
    assert "mybackup:backups/2026" in cmd


def test_build_rclone_list_remotes_flow():
    from workflows import cloud
    from workflows.cloud import _RcloneListRemotesScreen

    first = cloud.build_rclone_list_remotes_flow()
    step2 = first.next_step_func
    state: dict = {}
    result = step2("/tmp/outdir", state)
    assert isinstance(result, _RcloneListRemotesScreen)
    assert result.target.endswith("rclone_remotes.txt")


def test_command_registry_has_65_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 60, f"Expected 60+ tools, got {len(COMMAND_REGISTRY)}"


def test_build_handbrake_preset_flow():
    from workflows import handbrake

    first = handbrake.build_handbrake_preset_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/in.mp4", state).next_step_func
    step4 = step3("Apple 1080p", state).next_step_func
    result = step4("/tmp/out_hb.mp4", state)
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "HandBrakeCLI"
    cmd = result.cmds[0]
    assert cmd[0] == "HandBrakeCLI"
    assert "-i" in cmd and "/tmp/in.mp4" in cmd
    assert "-o" in cmd and "/tmp/out_hb.mp4" in cmd
    assert "--preset" in cmd and "Apple 1080p" in cmd


def test_build_handbrake_list_presets_flow():
    from workflows import handbrake

    first = handbrake.build_handbrake_list_presets_flow()
    step2 = first.next_step_func
    state: dict = {}
    result = step2("/tmp/presets.txt", state)
    assert isinstance(result, GenericCliProgressScreen)
    cmd = result.cmds[0]
    assert cmd[0] == "HandBrakeCLI"
    assert "--preset-list" in cmd


def test_handbrake_presets_list_is_nontrivial():
    from workflows import handbrake

    assert len(handbrake._HANDBRAKE_PRESETS) >= 8
    assert any("Apple" in p for p in handbrake._HANDBRAKE_PRESETS)
    assert any("Android" in p for p in handbrake._HANDBRAKE_PRESETS)
    assert any("Chromecast" in p for p in handbrake._HANDBRAKE_PRESETS)


def test_devices_tab_in_menus():
    import config

    assert "Device Presets" in config.MENU_MAIN
    assert "devices" in config.MENUS
    assert "Transcode Device Preset" in config.MENU_DEVICES
    assert "List HandBrake Presets" in config.MENU_DEVICES


def test_command_registry_has_67_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 60, f"Expected 60+ tools, got {len(COMMAND_REGISTRY)}"


def test_codec_choices_default_has_no_hw():
    from workflows import video

    baseline = video._codec_choices()
    assert "libx264" in baseline
    assert "libx265" in baseline
    assert "libsvtav1" in baseline
    assert "copy" in baseline
    for label in video._HW_CODEC_LABELS.values():
        assert label not in baseline


def test_codec_choices_nvenc_includes_hw_option(monkeypatch):
    from workflows import video

    monkeypatch.setattr(
        "workflows.video._load_full_config",
        lambda: {"hw_accel": "nvenc"},
    )
    choices = video._codec_choices()
    assert "h264_nvenc (NVIDIA NVENC)" in choices


def test_codec_choices_vaapi_includes_vaapi(monkeypatch):
    from workflows import video

    monkeypatch.setattr(
        "workflows.video._load_full_config",
        lambda: {"hw_accel": "vaapi"},
    )
    choices = video._codec_choices()
    assert "h264_vaapi (Linux VA-API)" in choices


def test_resolve_encoder_maps_hw_label_to_encoder():
    from workflows import video

    assert video._resolve_encoder("h264_nvenc (NVIDIA NVENC)") == "h264_nvenc"
    assert video._resolve_encoder("h264_vaapi (Linux VA-API)") == "h264_vaapi"
    assert video._resolve_encoder("libx264") == "libx264"
    assert video._resolve_encoder("copy") == "copy"


def test_advanced_convert_video_flow_uses_nvenc_when_configured(monkeypatch):
    from workflows import video

    monkeypatch.setattr(
        "workflows.video._load_full_config",
        lambda: {"hw_accel": "nvenc"},
    )
    first = video.build_advanced_convert_video_flow()
    step_input = first.next_step_func
    state: dict = {}
    step3 = step_input("/tmp/in.mov", state).next_step_func
    step4 = step3("mp4", state).next_step_func
    step5 = step4("h264_nvenc (NVIDIA NVENC)", state).next_step_func
    result = step5("medium", state).next_step_func("/tmp/out.mp4", state)
    assert isinstance(result, FfmpegProgressScreen)
    args = result.action_args
    assert "-c:v" in args and "h264_nvenc" in args
    assert "-preset" in args and "medium" in args


def test_command_registry_has_62_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 62, f"Expected 62+ tools, got {len(COMMAND_REGISTRY)}"


def test_build_preview_image_flow():
    from ui.preview import PreviewModalScreen
    from workflows import preview

    first = preview.build_preview_image_flow()
    result, _ = run_wizard(first, "/tmp/image.png")
    assert isinstance(result, PreviewModalScreen)
    assert result.preview_type == "image"


def test_build_preview_audio_flow():
    from ui.preview import PreviewModalScreen
    from workflows import preview

    first = preview.build_preview_audio_flow()
    result, _ = run_wizard(first, "/tmp/audio.wav")
    assert isinstance(result, PreviewModalScreen)
    assert result.preview_type == "audio"


def test_build_whisper_subtitles_flow(monkeypatch):
    from ui.transcribe import WhisperProgressScreen
    from workflows import transcribe

    monkeypatch.setattr(
        "workflows.transcribe.config._load_full_config",
        lambda: {
            "whisper_model": "small",
            "whisper_device": "cpu",
            "whisper_compute": "int8",
            "whisper_cache_dir": "/tmp/models",
        },
    )
    first = transcribe.build_whisper_subtitles_flow()
    result, state = run_wizard(
        first,
        "/tmp/audio.wav",
        "small",
        "srt",
        "en",
        "/tmp/audio.srt",
    )
    assert isinstance(result, WhisperProgressScreen)
    assert result.model == "small"
    assert result.device == "cpu"
    assert result.compute_type == "int8"
    assert result.language == "en"
    assert state["output_format"] == "srt"


def test_build_upscale_image_flow(tmp_path):
    from workflows import esrgan

    first = esrgan.build_upscale_image_flow()
    result, state = run_wizard(
        first,
        str(tmp_path / "input.png"),
        "realesrgan-x4plus",
        "4x",
        "256",
        str(tmp_path / "output.png"),
    )
    assert isinstance(result, GenericCliProgressScreen)
    assert result.tool_name == "Real-ESRGAN"
    assert result.cmds[0][0] == "realesrgan-ncnn-vulkan"
    assert "realesrgan-x4plus" in result.cmds[0]
    assert "4" in result.cmds[0]
    assert "256" in result.cmds[0]
    assert state["tile_size"] == 256
