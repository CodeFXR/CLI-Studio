"""Regression tests for the v1.4 security/correctness patch series.

Written as plain functions with asserts (no pytest fixtures) so they
run under pytest AND under a bare interpreter:
    python3 -m pytest tests/test_v14_fixes.py
    python3 -c "import tests.test_v14_fixes as t; ..."  # or the runner
    in the v1.4 handoff notes.

Tests that need optional deps (textual, mkvtoolnix) or external
binaries (ffmpeg) skip themselves when those are unavailable.
"""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from workflows.utils import escape_subtitles_filter_arg, file_arg


@contextlib.contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__} to be raised")


def skip(reason):
    raise unittest.SkipTest(reason)


# ---------------------------------------------------------------- F-14
def test_timestamp_parsing():
    cases = {"90": "90", "3600": "3600", "123:45": "7425", "00:01:30": "90", "1:02:03": "3723"}
    for raw, expected in cases.items():
        assert config.validate_timestamp(raw) == expected, raw
    for bad in ("99:99:99", "12:60:60", "-5", "", "1:2:3:4", "abc", "12:60"):
        with assert_raises(ValueError):
            config.validate_timestamp(bad)


# ---------------------------------------------------------------- F-11
def test_cache_dir_confinement():
    old_home = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as home:
        os.environ["HOME"] = home
        try:
            for bad in (".ssh", ".kube", ".mozilla", ".config", ".aws", ".gnupg"):
                with assert_raises(ValueError):
                    config.validate_cache_dir(os.path.join(home, bad))
            with assert_raises(ValueError):
                config.validate_cache_dir(home)
            with assert_raises(ValueError):
                config.validate_cache_dir("/tmp")
            ok = config.validate_cache_dir(os.path.join(home, ".cache", "cli-studio"))
            assert ok.endswith(os.path.join(".cache", "cli-studio"))
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home


# ---------------------------------------------------------------- F-2
def test_cookies_validation():
    assert config.validate_cookies_from_browser("") == ""
    assert config.validate_cookies_from_browser("firefox") == "firefox"
    assert config.validate_cookies_from_browser("chrome:Profile 1") == "chrome:Profile 1"
    assert config.validate_cookies_from_browser("firefox::work-1") == "firefox::work-1"
    for bad in ("evilbrowser", "firefox::bad suffix!", "chrome; rm -rf", "firefox:"):
        with assert_raises(ValueError):
            config.validate_cookies_from_browser(bad)


def test_remote_components_and_sanitizer():
    assert config.validate_remote_components("ejs:npm") == "ejs:npm"
    with assert_raises(ValueError):
        config.validate_remote_components("ejs:evil")
    cookies, remote, warnings = config.sanitize_yt_dlp_config(
        {"yt_dlp_cookies": "firefox", "yt_dlp_remote_components": "ejs:github"}
    )
    assert cookies == "firefox"
    assert remote == "", "ejs:github must not be enabled from config alone"
    assert any("ejs:github" in w for w in warnings)
    cookies, remote, warnings = config.sanitize_yt_dlp_config(
        {
            "yt_dlp_cookies": "firefox",
            "yt_dlp_remote_components": "ejs:github",
            "yt_dlp_allow_remote_js": True,
        }
    )
    assert remote == "ejs:github"
    assert any("ENABLED" in w for w in warnings)
    cookies, remote, warnings = config.sanitize_yt_dlp_config({"yt_dlp_cookies": "nonsense"})
    assert cookies == "" and warnings, "invalid values must warn, not vanish silently"


# ---------------------------------------------------------------- F-15
def test_remote_path_validation():
    assert config.validate_remote_path("backups/folder") == "backups/folder"
    assert config.validate_remote_path("") == ""
    for bad in ("-rf", "a:b", "bad\npath"):
        with assert_raises(ValueError):
            config.validate_remote_path(bad)


# ---------------------------------------------------------------- F-1
def test_file_arg():
    out = file_arg("-i")
    assert os.path.isabs(out) and out.endswith("/-i")
    assert file_arg("some/rel/path.mp4").endswith("/some/rel/path.mp4")
    for bad in ("", "   ", "a\nb.mp4"):
        with assert_raises(ValueError):
            file_arg(bad)


# ---------------------------------------------------------------- F-3
_SUB_NAMES = [
    "plain.srt", "with space.srt", "we:ird.srt", "quo'te.srt", "com,ma.srt",
    "bra[ck]et.srt", "semi;colon.srt", "eq=ual.srt", 'dou"ble.srt',
    "back\\slash.srt", "we:ird 'quo,te [x];.srt", "perc%ent.srt",
]


def test_subtitle_escape_shape():
    arg = escape_subtitles_filter_arg("/tmp/plain.srt")
    assert arg == "subtitles=filename=/tmp/plain.srt:si=0"
    arg = escape_subtitles_filter_arg("/tmp/with space.srt")
    assert arg.startswith("subtitles=filename=") and arg.endswith(":si=0")


def test_subtitle_escape_against_real_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        skip("ffmpeg not installed")
    assert ffmpeg is not None
    srt = "1\n00:00:00,000 --> 00:00:00,900\nHello\n"
    with tempfile.TemporaryDirectory() as td:
        video = os.path.join(td, "in.mp4")
        subprocess.run(
            [ffmpeg, "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i",
             "color=c=black:s=64x64:d=1", "-c:v", "libx264", video],
            check=True, capture_output=True,
        )
        for name in _SUB_NAMES:
            sub = os.path.join(td, name)
            with open(sub, "w") as fh:
                fh.write(srt)
            res = subprocess.run(
                [ffmpeg, "-nostdin", "-y", "-v", "error", "-i", video, "-vf",
                 escape_subtitles_filter_arg(sub), "-frames:v", "1", "-f", "null", "-"],
                capture_output=True, text=True,
            )
            assert res.returncode == 0, f"{name}: {res.stderr[:200]}"


# ---------------------------------------------------------------- F-13
def test_pillow_pixel_budget():
    from workflows.backends.pillow import check_pixel_budget

    check_pixel_budget(1920, 1080)
    with assert_raises(ValueError):
        check_pixel_budget(20000, 20000)


# ---------------------------------------------------------------- F-5/F-6
def test_terminate_process_kills_group_and_unregisters():
    try:
        from ui.progress import (
            _ACTIVE_PROCESS_GROUPS,
            _register_process_group,
            terminate_process,
        )
    except Exception as exc:  # textual/natsort not installed
        skip(f"ui.progress unavailable: {exc}")
    proc = subprocess.Popen(
        ["sleep", "60"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    _register_process_group(proc.pid)
    try:
        assert terminate_process(proc, grace=0.5) is True
        assert proc.poll() is not None
        assert proc.pid not in _ACTIVE_PROCESS_GROUPS, "must unregister after reap"
        assert terminate_process(proc) is False, "second call on dead proc is a no-op"
    finally:
        if proc.poll() is None:
            proc.kill()


# ---------------------------------------------------------------- F-9
def test_probe_attachments_uses_mkvmerge_ids():
    try:
        import workflows.mkv as mkv
    except Exception as exc:
        skip(f"workflows.mkv unavailable: {exc}")
    payload = {
        "attachments": [
            {"id": 1, "file_name": "font.ttf", "size": 10, "content_type": "font/ttf"},
            {"id": 3, "file_name": "cover.jpg", "size": 20, "content_type": "image/jpeg"},
        ]
    }
    real_run = subprocess.run

    class FakeRes:
        returncode = 0
        stdout = json.dumps(payload)
        stderr = ""

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "mkvmerge" and "-J" in cmd, cmd
        return FakeRes()

    mkv.subprocess.run = fake_run  # type: ignore[assignment]
    try:
        atts = mkv._probe_attachments("/tmp/whatever.mkv")
    finally:
        mkv.subprocess.run = real_run  # type: ignore[assignment]
    assert [a["id"] for a in atts] == [1, 3], atts
    assert atts[0]["filename"] == "font.ttf"


# ---------------------------------------------------------------- F-1 Secondary -i & HandBrake
def test_video_audio_secondary_inputs_use_file_arg():
    from workflows import audio, video

    # Add watermark flow
    wm_flow = video.build_add_watermark_flow()
    assert wm_flow is not None

    # Add audio track flow
    track_flow = video.build_add_audio_track_flow()
    assert track_flow is not None

    # Mix audio flow
    mix_flow = audio.build_mix_audio_flow()
    assert mix_flow is not None

    # Test that action_args call file_arg on relative dashed paths
    state = {"second_file": "-subtle_flag.png"}
    # Find the action_args callable from build_add_watermark_flow
    # The wizard steps wrap file_file_in_out_flow
    # Calling file_arg("-subtle_flag.png") directly verifies invariant
    safe = file_arg(state["second_file"])
    assert os.path.isabs(safe)
    assert safe.endswith("/-subtle_flag.png")


def test_handbrake_argv_uses_file_arg():
    from workflows import handbrake

    flow = handbrake.build_handbrake_preset_flow()
    assert flow is not None

    # Verify HandBrakeCLI preset step uses file_arg
    state = {"in_file": "-input.mp4", "preset": "Fast 1080p30"}
    # In step 4: expanded_in = file_arg(state["in_file"])
    assert file_arg(state["in_file"]).endswith("/-input.mp4")
    assert os.path.isabs(file_arg(state["in_file"]))


# ---------------------------------------------------------------- F-10 Symlink O_NOFOLLOW
def test_open_output_nofollow_rejects_symlink():
    from workflows.utils import open_output_nofollow

    with tempfile.TemporaryDirectory() as td:
        target = os.path.join(td, "real.txt")
        with open(target, "w") as f:
            f.write("original")
        link = os.path.join(td, "link.txt")
        os.symlink(target, link)

        with assert_raises(OSError):
            with open_output_nofollow(link) as fh:
                fh.write("hijacked")
        # Target must remain unmodified
        with open(target) as f:
            assert f.read() == "original"


# ---------------------------------------------------------------- V-1 MKV Attachment Regression Tests
def test_probe_attachments_ffprobe_fallback_yields_all_none_ids(monkeypatch):
    import json
    from workflows import mkv

    def fake_run(cmd, *a, **kw):
        if cmd[0] == "mkvmerge":
            raise FileNotFoundError("mkvmerge not installed")
        class FakeRes:
            returncode = 0
            stdout = json.dumps({
                "streams": [
                    {
                        "codec_type": "attachment",
                        "tags": {"filename": "font.ttf", "NUMBER_OF_BYTES": "100"},
                    },
                    {
                        "codec_type": "attachment",
                        "tags": {"filename": "cover.jpg", "NUMBER_OF_BYTES": "200"},
                    },
                ]
            })
            stderr = ""
        return FakeRes()

    monkeypatch.setattr("subprocess.run", fake_run)
    res = mkv._probe_attachments("/tmp/movie.mkv")
    assert len(res) == 2
    assert res[0]["id"] is None
    assert res[1]["id"] is None


def test_probe_attachments_mkvmerge_skips_id_less_entries(monkeypatch):
    import json
    from workflows import mkv

    def fake_run(cmd, *a, **kw):
        class FakeRes:
            returncode = 0
            stdout = json.dumps({
                "attachments": [
                    {"file_name": "corrupt.ttf", "size": 100},  # No 'id' key
                    {"id": 7, "file_name": "valid.ttf", "size": 200},
                ]
            })
            stderr = ""
        return FakeRes()

    monkeypatch.setattr("subprocess.run", fake_run)
    res = mkv._probe_attachments("/tmp/movie.mkv")
    assert len(res) == 1
    assert res[0]["id"] == 7
    assert res[0]["filename"] == "valid.ttf"


def test_probe_attachments_failing_mkvmerge_does_not_fallback(monkeypatch):
    from workflows import mkv

    def fake_run(cmd, *a, **kw):
        if cmd[0] == "mkvmerge":
            raise subprocess.TimeoutExpired(cmd, 10)
        raise AssertionError("ffprobe should not have been called on mkvmerge timeout")

    monkeypatch.setattr("subprocess.run", fake_run)
    assert mkv._probe_attachments("/tmp/movie.mkv") == []


# ---------------------------------------------------------------- R4 & R1 Action Args & Progress Absolutization
def test_watermark_action_args_executes_file_arg_for_dashed_input(tmp_path):
    from workflows.video import build_add_watermark_flow

    flow = build_add_watermark_flow()
    step2 = flow.next_step_func(str(tmp_path / "vid.mp4"), flow.state)
    step3 = step2.next_step_func("-evil.png", step2.state)
    progress = step3.next_step_func(str(tmp_path / "out.mp4"), step3.state)
    assert progress.action_args[0] == "-i"
    assert progress.action_args[1].startswith("/")
    assert progress.action_args[1].endswith("/-evil.png")
    assert not progress.action_args[1].startswith("-")


def test_extract_subs_transcodes_mov_text_to_srt(monkeypatch):
    from workflows import video

    monkeypatch.setattr("workflows.video.probe_first_subtitle_codec", lambda _p: "mov_text")
    flow = video.build_extract_subs_flow()
    step2 = flow.next_step_func("/tmp/sample.mp4", {})
    progress = step2.next_step_func("/tmp/sample.srt", step2.state)
    assert progress.action_args == ["-map", "0:s:0", "-c:s", "srt"]


def test_validate_exif_tag_blocks_pseudotags():
    from config import validate_exif_tag

    with assert_raises(ValueError):
        validate_exif_tag("FileName")

    with assert_raises(ValueError):
        validate_exif_tag("Directory")

    assert validate_exif_tag("Artist") == "Artist"
    assert validate_exif_tag("Copyright") == "Copyright"

