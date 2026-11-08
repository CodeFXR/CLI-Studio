import pytest
from pathlib import Path
from typing import Any
from PIL import Image
from textual.widgets import OptionList

from ui.progress import FfmpegProgressScreen, PillowProgressScreen, _ffmpeg_overwrite_flag
from ui.transcribe import _format_subtitle_timestamp
from workflows.backends import (
    ChafaBackend,
    EsrganBackend,
    GalleryDlBackend,
    ImageMagickBackend,
    PillowBackend,
    WhisperBackend,
    YtDlpBackend,
    backend_registry,
)
from workflows.plugins import load_plugins


def run_wizard(first_modal, *inputs: str, state: dict | None = None):
    """Step through a wizard by calling each next_step_func in turn.

    Mirror of the helper in test_workflows.py — duplicated here so the
    phase-7 tests don't depend on test_workflows being collected.
    """
    if state is None:
        state = {}
    current = first_modal
    for value in inputs:
        next_step = current.next_step_func
        current = next_step(value, state)
    return current, state


def test_backend_registry_has_phase_seven_backends():
    expected = {"chafa", "esrgan", "gallery-dl", "imagemagick", "pillow", "whisper", "yt-dlp"}
    assert expected <= set(backend_registry.names())
    assert isinstance(backend_registry.get("chafa"), ChafaBackend)
    assert isinstance(backend_registry.get("esrgan"), EsrganBackend)
    assert isinstance(backend_registry.get("imagemagick"), ImageMagickBackend)
    assert isinstance(backend_registry.get("image_magick"), ImageMagickBackend)
    assert isinstance(backend_registry.get("pillow"), PillowBackend)
    assert isinstance(backend_registry.get("whisper"), WhisperBackend)
    assert isinstance(backend_registry.get("yt-dlp"), YtDlpBackend)
    assert isinstance(backend_registry.get("yt_dlp"), YtDlpBackend)
    assert isinstance(backend_registry.get("gallery-dl"), GalleryDlBackend)
    assert isinstance(backend_registry.get("gallery_dl"), GalleryDlBackend)


def test_imagemagick_backend_builds_single_and_batch_commands(tmp_path):
    backend = ImageMagickBackend()
    input_file = tmp_path / "input.png"
    output_file = tmp_path / "output.png"
    single = backend.build_commands(str(input_file), str(output_file), ["-monochrome"])
    assert single == [["magick", str(input_file), "-monochrome", str(output_file)]]

    input_dir = tmp_path / "images"
    output_dir = tmp_path / "converted"
    input_dir.mkdir()
    (input_dir / "10.png").write_bytes(b"png")
    (input_dir / "2.png").write_bytes(b"png")
    batch = backend.build_commands(str(input_dir), str(output_dir), ["-negate"])
    assert [command[1] for command in batch] == [
        str(input_dir / "2.png"),
        str(input_dir / "10.png"),
    ]
    assert all(command[2] == "-negate" for command in batch)
    assert output_dir.is_dir()


def test_ytdlp_backend_builds_configured_command(tmp_path):
    command = YtDlpBackend().build_command(
        "https://example.com/video",
        str(tmp_path),
        cookies="chrome",
        remote_components="ejs:github",
        is_audio=True,
        is_playlist=True,
    )
    assert command[:4] == ["yt-dlp", "--newline", "--js-runtimes", "node"]
    assert ["--cookies-from-browser", "chrome"] == command[4:6]
    assert "--remote-components" in command
    assert ["-x", "--audio-format", "mp3"] == command[8:11]
    assert "--yes-playlist" in command
    assert command[-2:] == ["--", "https://example.com/video"]


def test_gallery_dl_backend_builds_command(tmp_path):
    command = GalleryDlBackend().build_command("https://example.com/gallery", str(tmp_path))
    assert command == ["gallery-dl", "--dest", str(tmp_path), "--", "https://example.com/gallery"]


def test_chafa_backend_builds_preview_commands(tmp_path):
    backend = ChafaBackend()
    image = str(tmp_path / "image.png")
    render = backend.build_render_command(image, width=60, height=20)
    waveform = backend.build_waveform_command("/tmp/audio.wav", image)
    assert render == ["chafa", "--size", "60x20", "--format", "symbols", image]
    assert waveform[0] == "ffmpeg"
    assert "showwaves=s=1920x240" in waveform[waveform.index("-filter_complex") + 1]


def test_chafa_waveform_honors_ffmpeg_overwrite_setting(monkeypatch):
    """ChafaBackend.build_waveform_command must respect the ffmpeg_overwrite
    config setting (instead of hardcoding -y)."""
    import config

    monkeypatch.setattr(config, "_load_full_config", lambda: {"ffmpeg_overwrite": False})
    backend = ChafaBackend()
    cmd = backend.build_waveform_command("/tmp/audio.wav", "/tmp/wave.png")
    assert cmd[1] == "-n", f"Expected -n (no-overwrite) but got {cmd[1]!r}"

    monkeypatch.setattr(config, "_load_full_config", lambda: {"ffmpeg_overwrite": True})
    cmd = backend.build_waveform_command("/tmp/audio.wav", "/tmp/wave.png")
    assert cmd[1] == "-y", f"Expected -y (overwrite) but got {cmd[1]!r}"


def test_esrgan_backend_builds_upscale_command(tmp_path):
    command = EsrganBackend().build_command(
        str(tmp_path / "input.png"),
        str(tmp_path / "output.png"),
        model="realesrgan-x4plus",
        scale=4,
        tile_size=256,
    )
    assert command[0] == "realesrgan-ncnn-vulkan"
    assert command[command.index("-n") + 1] == "realesrgan-x4plus"
    assert command[command.index("-s") + 1] == "4"
    assert command[command.index("-t") + 1] == "256"


def test_whisper_backend_options_and_timestamps():
    backend = WhisperBackend()
    assert "small" in backend.models
    assert "large-v3" in backend.models
    assert _format_subtitle_timestamp(65.432) == "00:01:05,432"
    assert _format_subtitle_timestamp(65.432, vtt=True) == "00:01:05.432"


def test_pillow_progress_screen_uses_pillow_backend():
    screen = PillowProgressScreen("/tmp/input.png", "/tmp/output.png", "resize", (2, 2))
    image = Image.new("RGB", (4, 4), "white")
    processed = screen.process_image(image)
    assert processed.size == (2, 2)


def test_pillow_progress_screen_inherits_logging_mixin():
    """PillowProgressScreen must inherit _LoggingModalScreen so the batch failure
    path at ui/progress.py:461-466 can call self.write_log / self._log_msg
    without raising AttributeError. The mixin is the contract for all four
    progress screens.
    """
    from ui.progress import _LoggingModalScreen

    assert _LoggingModalScreen in PillowProgressScreen.__mro__
    screen = PillowProgressScreen("/tmp/in.png", "/tmp/out.png", "resize")
    assert callable(screen.write_log)
    assert callable(screen._log_msg)


@pytest.mark.asyncio
async def test_pillow_progress_screen_log_msg_uses_active_theme(monkeypatch):
    """The new _log_msg method on PillowProgressScreen renders a markup line
    coloured by the active theme's accent/fail colors."""
    import cli_studio_app

    monkeypatch.setattr(cli_studio_app, "_load_full_config", lambda: {"default_theme": "t-default"})
    monkeypatch.setattr(cli_studio_app, "load_plugins", lambda *args, **kwargs: 0)
    test_app = cli_studio_app.CliStudioApp()
    async with test_app.run_test():
        from ui.progress import _LoggingModalScreen

        class _FakeScreen(_LoggingModalScreen):
            def __init__(self, owner):
                self.app = owner

        screen = _FakeScreen(test_app)
        line = screen._log_msg("failed", "test.png (broken)")
        assert line.startswith("[bold")
        assert "Failed:" in line
        assert "test.png" in line
        exec_line = screen._log_msg("executing", "ffmpeg -i in.mp4 out.mp4")
        assert "Executing:" in exec_line
        assert line.startswith("[bold")
        assert "Failed:" in line
        assert "test.png" in line
        exec_line = screen._log_msg("executing", "ffmpeg -i in.mp4 out.mp4")
        assert "Executing:" in exec_line


def test_ffmpeg_overwrite_setting_controls_flag(monkeypatch):
    import config

    monkeypatch.setattr(config, "_load_full_config", lambda: {"ffmpeg_overwrite": False})
    assert _ffmpeg_overwrite_flag() == "-n"
    monkeypatch.setattr(config, "_load_full_config", lambda: {"ffmpeg_overwrite": True})
    assert _ffmpeg_overwrite_flag() == "-y"


def test_rclone_copy_flow_rejects_malicious_remote_name():
    """validate_remote_name rejects flag-like and shell-metacharacter inputs."""
    from workflows import cloud

    for bad in ("--config=/etc/rclone.conf", "my remote", "foo:bar", ""):
        first = cloud.build_rclone_copy_flow()
        step_input = first.next_step_func
        state: dict = {}
        remote_name_picker = step_input("/tmp/local", state)
        step_validate = remote_name_picker.next_step_func
        try:
            step_validate(bad, state)
        except ValueError:
            continue
        raise AssertionError(f"validate_remote_name should reject {bad!r}")


def test_extract_subs_includes_copy_codec_to_avoid_reencode():
    """The new extract_subs flow uses -c:s copy to avoid re-encoding subtitle streams.

    Re-encoding subtitle streams silently corrupts the output (e.g. ASS → SRT
    loses styling). -c:s copy preserves the source codec bit-for-bit.
    """
    from workflows import video

    first = video.build_extract_subs_flow()
    result, _ = run_wizard(first, "/tmp/v.mkv", "/tmp/v_subs.srt")
    assert isinstance(result, FfmpegProgressScreen)
    assert "-c:s" in result.action_args
    assert "copy" in result.action_args


def test_backend_base_enforces_name_and_operations():
    """Backend subclasses must declare name and operations; missing either raises TypeError at class-definition time."""
    from workflows.backends.base import Backend

    class ValidBackend(Backend):
        name = "valid"
        operations = frozenset({"foo"})

        def __init__(self) -> None:
            pass

    ValidBackend()

    try:

        class MissingName(Backend):
            operations = frozenset({"foo"})

            def __init__(self) -> None:
                pass
    except TypeError as exc:
        assert "name" in str(exc), exc
    else:
        raise AssertionError("Backend missing 'name' should raise TypeError")

    try:

        class MissingOps(Backend):
            name = "noname"

            def __init__(self) -> None:
                pass
    except TypeError as exc:
        assert "operations" in str(exc), exc
    else:
        raise AssertionError("Backend missing 'operations' should raise TypeError")


def test_unique_path_avoids_collisions(tmp_path):
    """unique_path returns the first candidate that does not exist; appends _N otherwise."""
    from workflows.utils import unique_path

    (tmp_path / "clip.mp4").touch()
    (tmp_path / "clip_2.mp4").touch()

    p1 = unique_path(str(tmp_path), "clip", ".mp4")
    assert p1.endswith("clip_3.mp4")

    Path(p1).touch()
    p2 = unique_path(str(tmp_path), "clip", ".mp4")
    assert p2.endswith("clip_4.mp4")

    p3 = unique_path(str(tmp_path), "fresh", "mp4")
    assert p3.endswith("fresh.mp4")


def test_plugin_loader_registers_commands_menus_and_help(tmp_path):
    plugin = tmp_path / "demo.py"
    plugin.write_text(
        "PLUGIN_REGISTRY = {'demo tool': lambda: None}\n"
        "PLUGIN_HELP = {'demo tool': 'A demo tool.'}\n",
        encoding="utf-8",
    )
    registry = {"built-in": lambda: None}
    menus: dict[str, list[str]] = {"main": []}
    help_registry: dict[str, str] = {}

    loaded = load_plugins(registry, tmp_path, menus=menus, help_registry=help_registry)

    assert loaded == 1
    assert callable(registry["demo tool"])
    assert "demo tool" in menus["plugins"]
    assert "Plugins" in menus["main"]
    assert help_registry["demo tool"] == "A demo tool."


def test_plugin_loader_preserves_builtins_and_skips_private_files(tmp_path):
    (tmp_path / "collision.py").write_text(
        "PLUGIN_REGISTRY = {'built-in': lambda: 'plugin', 'new tool': lambda: None}\n",
        encoding="utf-8",
    )
    (tmp_path / "_private.py").write_text(
        "PLUGIN_REGISTRY = {'private tool': lambda: None}\n",
        encoding="utf-8",
    )

    def builtin():
        return "builtin"

    registry = {"built-in": builtin}

    loaded = load_plugins(registry, tmp_path)

    assert loaded == 1
    assert registry["built-in"] is builtin
    assert "private tool" not in registry
    assert "new tool" in registry


def test_plugin_loader_continues_after_broken_plugin(tmp_path):
    (tmp_path / "broken.py").write_text("raise RuntimeError('broken')\n", encoding="utf-8")
    (tmp_path / "working.py").write_text(
        "PLUGIN_REGISTRY = {'working tool': lambda: None}\n",
        encoding="utf-8",
    )
    registry: dict[str, Any] = {}

    loaded = load_plugins(registry, tmp_path)

    assert loaded == 1
    assert "working tool" in registry


def test_plugin_loader_creates_missing_directory(tmp_path):
    plugin_dir = tmp_path / "nested" / "plugins"
    registry: dict[str, Any] = {}

    assert load_plugins(registry, plugin_dir) == 0
    assert plugin_dir.is_dir()


@pytest.mark.asyncio
async def test_settings_command_opens_regular_menu(monkeypatch):
    import cli_studio_app

    from config import DEFAULT_CONFIG

    monkeypatch.setattr(cli_studio_app, "_load_full_config", lambda: dict(DEFAULT_CONFIG))
    monkeypatch.setattr(cli_studio_app, "load_plugins", lambda *args, **kwargs: 0)
    app = cli_studio_app.CliStudioApp()

    async with app.run_test() as pilot:
        await pilot.press(*list("/settings"), "enter")
        await pilot.pause()
        assert app.current_view() == "menu"
        assert app.menu_context == "settings"
        assert app.screen.has_class("menu-open")
        options = app.query_one("#menu-list", OptionList)
        option_ids = {
            str(options.get_option_at_index(index).id) for index in range(options.option_count)
        }
        assert "default_theme" not in option_ids
        assert {
            "yt_dlp_cookies",
            "yt_dlp_remote_components",
            "hw_accel",
            "ffmpeg_overwrite",
            "whisper_model",
        } <= option_ids


@pytest.mark.asyncio
async def test_settings_menu_saves_values(monkeypatch, tmp_path):
    import cli_studio_app
    import config

    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(cli_studio_app, "load_plugins", lambda *args, **kwargs: 0)
    app = cli_studio_app.CliStudioApp()

    async with app.run_test() as pilot:
        await pilot.press(*list("/settings"), "enter")
        await pilot.pause()
        app._handle_settings_selection("ffmpeg_overwrite")
        app._handle_settings_selection("hw_accel")
        app._handle_settings_selection("whisper_model")
        app._handle_settings_selection("yt_dlp_cookies")
        await pilot.press(*list("firefox"), "enter")
        await pilot.pause()

    saved = config._load_full_config()
    assert saved["default_theme"] == "t-default"
    assert saved["yt_dlp_cookies"] == "firefox"
    assert saved["hw_accel"] == "nvenc"
    assert saved["ffmpeg_overwrite"] is False
    assert saved["whisper_model"] == "medium"


def test_validate_quality_strict_integer_bounds():
    import config

    assert config.validate_quality("1") == "1"
    assert config.validate_quality("50") == "50"
    assert config.validate_quality("100") == "100"

    for invalid in ("0", "101", "-1", "abc", "50.5", ""):
        with pytest.raises(ValueError):
            config.validate_quality(invalid)


def test_pillow_progress_screen_rejects_symlink_output(tmp_path):
    import os
    from ui.progress import PillowProgressScreen

    real_file = tmp_path / "real.jpg"
    real_file.write_text("protected content")
    symlink_file = tmp_path / "symlink.jpg"
    os.symlink(real_file, symlink_file)
    input_file = tmp_path / "in.jpg"
    input_file.write_text("input")

    notified = []

    class FakeApp:
        def notify(self, msg, severity="info", timeout=5):
            notified.append((msg, severity))

        def call_from_thread(self, fn, *args, **kwargs):
            fn(*args, **kwargs)

    screen = PillowProgressScreen(str(input_file), str(symlink_file), "convert")
    screen.app = FakeApp()
    screen.run_pillow()

    assert any("symbolic link" in msg for msg, _ in notified)
    assert real_file.read_text() == "protected content"


def test_preview_kill_process_escalates_to_sigkill():
    import os
    import signal
    import subprocess
    import sys
    import textwrap
    import time
    from ui.preview import PreviewModalScreen

    script = textwrap.dedent("""\
    import signal, sys, time
    def handler(*a):
        pass
    signal.signal(signal.SIGTERM, handler)
    sys.stderr.write("ready\\n")
    sys.stderr.flush()
    time.sleep(60)
    """)
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        stderr=subprocess.PIPE,
    )
    assert proc.stderr is not None
    # Wait for child to be ready
    proc.stderr.readline()

    screen = PreviewModalScreen("/tmp/in.jpg", "image")
    screen.process = proc
    screen._kill_process()

    deadline = time.time() + 3
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.05)

    assert proc.returncode in (-signal.SIGKILL, -9)
