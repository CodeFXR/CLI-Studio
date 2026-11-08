"""Smoke test: verify every project module imports cleanly.

If this file fails, the package cannot start. Run it first.
"""

import importlib

PROJECT_MODULES = [
    "config",
    "studio_themes",
    "ui.screens",
    "ui.progress",
    "ui.preview",
    "ui.transcribe",
    "workflows.utils",
    "workflows.registry",
    "workflows.shared",
    "workflows.preview",
    "workflows.transcribe",
    "workflows.esrgan",
    "workflows.video",
    "workflows.audio",
    "workflows.image",
    "cli_studio",
    "cli_studio_app",
]


def test_all_modules_import():
    for name in PROJECT_MODULES:
        mod = importlib.import_module(name)
        assert mod is not None, f"Failed to import {name}"


def test_command_registry_has_55_tools():
    from workflows.registry import COMMAND_REGISTRY

    assert len(COMMAND_REGISTRY) >= 55, (
        f"Expected 55+ tools in registry, got {len(COMMAND_REGISTRY)}: "
        f"{sorted(COMMAND_REGISTRY.keys())}"
    )


def test_expected_tools_registered():
    from workflows.registry import COMMAND_REGISTRY

    expected = {
        "download video",
        "download playlist",
        "convert video",
        "trim video",
        "extract audio",
        "mute video",
        "change video speed",
        "rotate video",
        "reverse video",
        "create gif",
        "extract frames",
        "add watermark",
        "add audio track",
        "scale/resize video",
        "fade in video",
        "extract subtitles",
        "generate whisper subtitles",
        "burn subtitles",
        "silence removal",
        "audio visualizer",
        "convert video preset",
        "remux video to mkv",
        "merge mkvs",
        "extract mkv subs",
        "add subs to mkv",
        "extract mkv attachments",
        "download gallery",
        "rclone copy",
        "rclone list remotes",
        "download audio",
        "convert audio",
        "trim audio",
        "change volume",
        "change audio speed",
        "reverse audio",
        "normalize audio",
        "fade in audio",
        "mix audio tracks",
        "normalize audio (2-pass)",
        "preview audio waveform",
        "transcode device preset",
        "list handbrake presets",
        "convert image",
        "resize image",
        "crop image",
        "rotate image",
        "flip image",
        "remove background color",
        "apply filter",
        "strip metadata",
        "add text watermark",
        "optimize/compress",
        "convert to pdf",
        "add border",
        "extract text from image",
        "preview image",
        "upscale image",
        "sprite sheet",
        "set exif tag",
        "copy exif",
        "rename by exif date",
        "scan barcode",
    }
    missing = expected - set(COMMAND_REGISTRY.keys())
    extra = set(COMMAND_REGISTRY.keys()) - expected
    assert not missing, f"Missing tools in registry: {sorted(missing)}"
    assert not extra, f"Unknown tools in registry: {sorted(extra)}"


def test_themes_registered():
    from studio_themes import NAME_TO_CLASS, THEME_NAMES, THEME_ORDER, THEMES_CSS

    assert len(THEME_ORDER) == len(THEME_NAMES) == len(NAME_TO_CLASS)
    assert len(THEME_ORDER) >= 1
    assert THEMES_CSS.strip(), "THEMES_CSS is empty"
    for key in THEME_ORDER:
        assert key in THEME_NAMES
        assert THEME_NAMES[key] in NAME_TO_CLASS
        assert NAME_TO_CLASS[THEME_NAMES[key]] == key


def test_app_class_and_version():
    import cli_studio_app

    assert cli_studio_app.CliStudioApp.__name__ == "CliStudioApp"
    assert cli_studio_app.CliStudioApp.VERSION.startswith("v"), "VERSION should look like vX.Y.Z"


def test_help_registry_fallback():
    from config import get_help

    download_help = get_help("download video")
    assert download_help and len(download_help) > 0
    assert "download" in download_help.lower()
    fallback = get_help("made up tool")
    assert "made up tool" in fallback or "follow the on-screen" in fallback.lower()


def test_help_registry_covers_every_command():
    """Every command in the registry should have a help entry (no fallback generic text).

    Help entries can be added later by appending to config.HELP_REGISTRY.
    The CLI-Studio project's promise to users is that '?' on any tool shows
    a meaningful explanation, not a placeholder.
    """
    from config import HELP_REGISTRY, get_help
    from workflows.registry import COMMAND_REGISTRY

    generic_phrase = "follow the on-screen"
    missing = []
    for cmd in COMMAND_REGISTRY:
        help_text = get_help(cmd)
        if cmd not in HELP_REGISTRY or generic_phrase in help_text.lower():
            missing.append(cmd)
    assert not missing, (
        f"These {len(missing)} tools lack dedicated help text (use the generic fallback): "
        f"{sorted(missing)}"
    )


def test_menus_reference_no_unknown_commands():
    """Every menu entry should either be a known submenu or a known command.

    Catches dead menu items like the historical 'Cloud Tools' before they ship.
    """
    from config import MENU_MAIN, MENU_VIDEO, MENU_AUDIO, MENU_IMAGE, MENU_CLOUD, MENU_DEVICES
    from workflows.registry import COMMAND_REGISTRY

    submenus = {
        "Video Tools",
        "Audio Tools",
        "Image Tools",
        "Device Presets",
        "Cloud Tools",
        "Settings",
    }
    for menu_name, items in [
        ("MENU_MAIN", MENU_MAIN),
        ("MENU_VIDEO", MENU_VIDEO),
        ("MENU_AUDIO", MENU_AUDIO),
        ("MENU_IMAGE", MENU_IMAGE),
        ("MENU_CLOUD", MENU_CLOUD),
        ("MENU_DEVICES", MENU_DEVICES),
    ]:
        unknown = [
            item for item in items if item not in submenus and item.lower() not in COMMAND_REGISTRY
        ]
        assert not unknown, (
            f"{menu_name} has entries with no matching submenu or command: {unknown}"
        )


def test_every_registered_command_appears_in_some_menu():
    """Reverse-direction guard: every entry in COMMAND_REGISTRY must appear in at
    least one MENU_* list (case-insensitive). Otherwise the user can never
    discover it via the menu.
    """
    from config import MENUS
    from workflows.registry import COMMAND_REGISTRY

    all_menu_items = {item.lower() for items in MENUS.values() for item in items}
    orphans = [cmd for cmd in COMMAND_REGISTRY if cmd.lower() not in all_menu_items]
    assert not orphans, (
        f"Commands registered but not in any menu (will be invisible to users): {orphans}"
    )


def test_validators_exist_and_reject_bad_input():
    from config import (
        validate_cache_dir,
        validate_coords,
        validate_decimal,
        validate_dimensions,
        validate_exif_tag,
        validate_remote_name,
        validate_resolution,
    )

    for fn, bad in [
        (validate_resolution, "not-a-resolution"),
        (validate_resolution, "0:0"),
        (validate_resolution, "1920:0"),
        (validate_resolution, "0:1080"),
        (validate_dimensions, "800-600"),
        (validate_dimensions, "0x0"),
        (validate_dimensions, "100x0"),
        (validate_dimensions, "0x100"),
        (validate_coords, "10 20 30"),
        (validate_decimal, "abc"),
        (validate_remote_name, "--config=/etc/rclone.conf"),
        (validate_remote_name, "my remote"),
        (validate_remote_name, ""),
        (validate_exif_tag, "-all"),
        (validate_exif_tag, "1Copyright"),
        (validate_exif_tag, ""),
        (validate_cache_dir, "/etc/passwd"),
        (validate_cache_dir, "/usr/local/share"),
    ]:
        try:
            fn(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{fn.__name__} should reject {bad!r}")


def test_validators_accept_good_input():
    from config import (
        validate_cache_dir,
        validate_exif_tag,
        validate_remote_name,
    )

    assert validate_remote_name("myremote") == "myremote"
    assert validate_remote_name("gdrive.backup") == "gdrive.backup"
    assert validate_remote_name("rclone-1") == "rclone-1"

    assert validate_exif_tag("Copyright") == "Copyright"
    assert validate_exif_tag("XMP:City") == "XMP:City"
    assert validate_exif_tag("Artist-1") == "Artist-1"

    assert validate_cache_dir("/tmp/whisper") == "/tmp/whisper"
    assert validate_cache_dir("/var/tmp/whisper") == "/var/tmp/whisper"
    assert validate_cache_dir("") == ""


def test_logging_mixin_used_by_progress_screens():
    from ui.progress import (
        DownloadProgressScreen,
        FfmpegProgressScreen,
        GenericCliProgressScreen,
        _LoggingModalScreen,
    )

    assert issubclass(DownloadProgressScreen, _LoggingModalScreen)
    assert issubclass(FfmpegProgressScreen, _LoggingModalScreen)
    assert issubclass(GenericCliProgressScreen, _LoggingModalScreen)


def test_base_input_modal_used_by_screen_classes():
    from ui.screens import (
        FilePickerScreen,
        OptionSelectScreen,
        TextInputScreen,
        _BaseInputModal,
    )

    assert issubclass(TextInputScreen, _BaseInputModal)
    assert issubclass(FilePickerScreen, _BaseInputModal)
    assert issubclass(OptionSelectScreen, _BaseInputModal)
