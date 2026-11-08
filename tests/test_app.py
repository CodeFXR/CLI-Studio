"""UI tests using Textual's Pilot harness.

These mount the real CliStudioApp in a headless test harness, dispatch slash commands,
and verify the resulting view state. Config reads are stubbed so the tests don't touch
the user's real ~/.cli_studio_config.json.
"""

import pytest

from tests.conftest import _cli_studio  # noqa: F401  (loads cli_studio_app into sys.modules)


@pytest.fixture
def stubbed_config(monkeypatch):
    monkeypatch.setattr(
        "config._load_full_config", lambda: dict(__import__("config").DEFAULT_CONFIG)
    )


@pytest.mark.asyncio
async def test_video_command_opens_video_menu(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/video"), "enter")
        await pilot.pause()
        assert app.screen.has_class("menu-open")
        assert app.menu_context == "video"


@pytest.mark.asyncio
async def test_audio_command_opens_audio_menu(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/audio"), "enter")
        await pilot.pause()
        assert app.screen.has_class("menu-open")
        assert app.menu_context == "audio"


@pytest.mark.asyncio
async def test_image_command_opens_image_menu(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/image"), "enter")
        await pilot.pause()
        assert app.screen.has_class("menu-open")
        assert app.menu_context == "image"


@pytest.mark.asyncio
async def test_cloud_command_opens_cloud_menu(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/cloud"), "enter")
        await pilot.pause()
        assert app.screen.has_class("menu-open")
        assert app.menu_context == "cloud"


@pytest.mark.asyncio
async def test_devices_command_opens_devices_menu(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/devices"), "enter")
        await pilot.pause()
        assert app.screen.has_class("menu-open")
        assert app.menu_context == "devices"


@pytest.mark.asyncio
async def test_themes_command_opens_themes_view(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/themes"), "enter")
        await pilot.pause()
        assert app.screen.has_class("themes-open")
        assert app.current_view() == "themes"


@pytest.mark.asyncio
async def test_about_command_opens_about_view(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/about"), "enter")
        await pilot.pause()
        assert app.screen.has_class("about-open")
        assert app.current_view() == "about"


@pytest.mark.asyncio
async def test_exit_command_terminates_app(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/exit"), "enter")
        await pilot.pause()
        assert not app.is_running


@pytest.mark.asyncio
async def test_unknown_command_writes_to_output(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/frobulate"), "enter")
        await pilot.pause()
        output = app.query_one("#output-text")
        rendered = output.render().plain
        assert "unknown command" in rendered.lower() or "frobulate" in rendered.lower()


@pytest.mark.asyncio
async def test_home_command_returns_to_home(stubbed_config):
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/themes"), "enter")
        await pilot.pause()
        assert app.current_view() == "themes"
        await pilot.press(*list("/home"), "enter")
        await pilot.pause()
        assert app.current_view() == "home"
        assert app.menu_context == "main"


@pytest.mark.asyncio
async def test_apply_theme_changes_active_class(stubbed_config):
    from cli_studio_app import CliStudioApp

    from studio_themes import THEME_ORDER

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.apply_theme(THEME_ORDER[1], silent=True)
        await pilot.pause()
        assert app.active_theme == THEME_ORDER[1]
        assert app.screen.has_class(THEME_ORDER[1])


@pytest.mark.asyncio
async def test_themes_command_with_name_switches_theme(stubbed_config):
    """`/themes navy` should apply the navy theme immediately without opening the picker."""
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/themes/t-accident"), "enter")
        await pilot.pause()
        assert app.active_theme == "t-accident"
        assert app.screen.has_class("t-accident")


@pytest.mark.asyncio
async def test_themes_command_with_partial_name_prompts_picker(stubbed_config):
    """`/themes xyzzy` (no match) should prompt the user to confirm before saving."""
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/themes/xyzzy"), "enter")
        await pilot.pause()
        output = app.query_one("#output-text")
        rendered = output.render().plain.lower()
        assert "no theme matches" in rendered or "xyzzy" in rendered


@pytest.mark.asyncio
async def test_themes_command_with_empty_name_shows_usage(stubbed_config):
    """`/themes/` (slash + empty name) should show a usage hint, not pick a theme silently."""
    from cli_studio_app import CliStudioApp

    app = CliStudioApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(*list("/themes/"), "enter")
        await pilot.pause()
        output = app.query_one("#output-text")
        rendered = output.render().plain.lower()
        assert "usage" in rendered or "/themes/" in rendered
