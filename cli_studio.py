#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import Any

try:
    import textual  # noqa: F401
except ModuleNotFoundError:
    if sys.prefix == sys.base_prefix:
        _venv_python = Path(__file__).resolve().parent / ".venv" / "bin" / "python3"
        if _venv_python.is_file():
            os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)
    raise

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Center, Container
from textual.screen import ModalScreen, Screen
from textual.suggester import Suggester
from textual.widgets import Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option

import config as app_config
from config import (
    DEFAULT_CONFIG,
    HELP_REGISTRY,
    MENUS,
    _load_full_config,
    _save_config,
    get_help,
)
from studio_themes import (
    LAYOUT_CSS,
    NAME_TO_CLASS,
    THEME_NAMES,
    THEME_ORDER,
    log_palette_colors,
    THEMES_CSS,
)
from workflows.plugins import load_plugins
from workflows.registry import COMMAND_REGISTRY, CommandHandler

Image: Any = None
try:
    from textual_image.widget import Image as _Image

    Image = _Image
    HAS_IMAGE_LIB = True
except ImportError:
    HAS_IMAGE_LIB = False

ASCII_ART = """
     ██████╗ ██╗     ██╗    ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗ 
    ██╔════╝ ██║     ██║    ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔══██╗
    ██║      ██║     ██║ ▶  ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║
    ██║      ██║     ██║    ╚════██║   ██║   ██║   ██║██║  ██║██║██║   ██║
    ╚██████╗ ███████╗██║    ███████║   ██║   ╚██████╔╝██████╔╝██║╚██████╔╝
     ╚═════╝ ╚══════╝╚═╝    ╚═════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ 
"""
HELP_TEXT = """
/home         go to main menu      esc
/menu         open tools menu      alt+m
/about        about CLI-Studio     alt+a
/themes       switch themes        alt+t
/settings     edit preferences     alt+s
/log          toggle debug log     ctrl+l
/back         go back              alt+b
/exit         exit the app         alt+e"""

ABOUT_TEXT = (
    "CLI ▶ Studio is a terminal user interface for image, video, and audio manipulation.\n"
    "It simplifies the use of command-line media tools by providing an intuitive, menu-driven workflow,\n"
    "allowing beginners to access core features without memorizing complex commands."
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_FILENAME = "cli-studio_icon.png"
_candidate_icon_paths = [
    os.path.join(SCRIPT_DIR, ICON_FILENAME),
    os.path.join(SCRIPT_DIR, "ui", ICON_FILENAME),
]
ICON_PATH = next((p for p in _candidate_icon_paths if os.path.exists(p)), _candidate_icon_paths[0])

_COMMANDS = {
    "/home": lambda s: s.action_go_home(),
    "/back": lambda s: s.action_go_back(),
    "/about": lambda s: s.action_show_about(),
    "/menu": lambda s: s.action_show_menu(),
    "/themes": lambda s: s.action_show_themes(),
    "/settings": lambda s: s.action_show_settings(),
    "/exit": lambda s: s.action_show_exit(),
    "/video": lambda s: s._enter_menu("video"),
    "/audio": lambda s: s._enter_menu("audio"),
    "/image": lambda s: s._enter_menu("image"),
    "/cloud": lambda s: s._enter_menu("cloud"),
    "/devices": lambda s: s._enter_menu("devices"),
}
_HW_ACCEL_OPTIONS = ("", "nvenc", "vaapi", "videotoolbox", "qsv")
_WHISPER_MODEL_OPTIONS = ("tiny", "base", "small", "medium", "large-v3")
_WHISPER_DEVICE_OPTIONS = ("auto", "cpu", "cuda")
_WHISPER_COMPUTE_OPTIONS = ("auto", "int8", "float16", "float32")


def get_ascii_art() -> str:
    lines = ASCII_ART.strip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


class HelpModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, title: str, body: str, theme_class: str | None = None):
        super().__init__()
        self.title = title
        self.body = body
        if theme_class:
            self.add_class(theme_class)

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Static(f"Help: {self.title}", id="confirm-question")
            yield Static(self.body, id="help-body")
            yield Static("Esc to close", id="confirm-help")

    def on_mount(self):
        if hasattr(self.app, "active_theme"):
            self.add_class(self.app.active_theme)


class ConfirmThemeScreen(ModalScreen[bool]):
    def __init__(self, theme_class: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.theme_class = theme_class
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Static("Set as default theme?", id="confirm-question")
            yield Static("", id="confirm-spacer")
            with Container(id="confirm-options"):
                yield Static("Yes", id="option-yes", classes="confirm-option selected")
                yield Static("No", id="option-no", classes="confirm-option")
            yield Static("", id="confirm-spacer2")
            yield Static("← → or tab to move  •  enter to select", id="confirm-help")

    def on_mount(self) -> None:
        for cls in THEME_ORDER:
            self.screen.remove_class(cls)
        theme = getattr(self.app, "active_theme", None)
        if isinstance(theme, str):
            self.screen.add_class(theme)

    def _update_selection(self) -> None:
        self.query_one("#option-yes").set_class(self.selected_index == 0, "selected")
        self.query_one("#option-no").set_class(self.selected_index == 1, "selected")

    def on_key(self, event) -> None:
        if event.key in ("left", "right", "tab"):
            self.selected_index = 1 - self.selected_index
            self._update_selection()
        elif event.key == "enter":
            self.dismiss(self.selected_index == 0)
        elif event.key == "escape":
            self.dismiss(False)


class CommandSuggester(Suggester):
    COMMANDS = [
        "/home",
        "/back",
        "/about",
        "/menu",
        "/themes",
        "/settings",
        "/exit",
        "/video",
        "/audio",
        "/image",
        "/cloud",
        "/devices",
    ]

    async def get_suggestion(self, value: str) -> str | None:
        if not value.startswith("/"):
            return None
        if value.startswith("/themes/"):
            prefix = "/themes/"
            part = value[len(prefix) :]
            if not part:
                return f"{prefix}{THEME_NAMES[THEME_ORDER[0]]}"
            for name in THEME_NAMES.values():
                if name.startswith(part):
                    return f"{prefix}{name}"
            for cls in THEME_ORDER:
                if cls.startswith(part):
                    return f"{prefix}{cls}"
            return None
        for c in self.COMMANDS:
            if c.startswith(value):
                return c
        return None


class CliStudioApp(App):
    TITLE = "CLI-Studio"
    VERSION = "v1.2.0"
    CSS = LAYOUT_CSS + THEMES_CSS
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "toggle_log", "Toggle Log"),
        ("escape", "go_home", "Home"),
        ("alt+a", "show_about", "About"),
        ("alt+m", "show_menu", "Menu"),
        ("alt+t", "show_themes", "Themes"),
        ("alt+s", "show_settings", "Settings"),
        ("alt+b", "go_back", "Back"),
        ("alt+e", "show_exit", "Exit"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_theme = self._load_theme_from_config()
        self.menu_context = "main"
        self.active_tool_name = None
        self.pending_setting = None
        self._view_stack: list[tuple[str, str]] = []

    def action_toggle_log(self) -> None:
        if self.screen.has_class("log-open"):
            self.screen.remove_class("log-open")
        else:
            self.screen.add_class("log-open")

    def action_show_help(self) -> None:
        if self.active_tool_name:
            self.push_themed_screen(
                HelpModal(
                    self.active_tool_name.title(),
                    get_help(self.active_tool_name),
                )
            )
        elif self.current_view() == "menu" and self.menu_context != "main":
            try:
                ol = self.query_one("#menu-list", OptionList)
                if ol.highlighted is not None:
                    opt = ol.get_option_at_index(ol.highlighted)
                    self.push_themed_screen(
                        HelpModal(
                            str(opt.id).title(),
                            get_help(str(opt.id).lower()),
                        )
                    )
            except Exception:
                pass

    def _load_theme_from_config(self) -> str:
        config = _load_full_config()
        theme = config.get("default_theme")
        if isinstance(theme, str) and theme in THEME_ORDER:
            return theme
        fallback = DEFAULT_CONFIG.get("default_theme")
        return fallback if isinstance(fallback, str) else THEME_ORDER[0]

    def _save_theme_to_config(self, theme_class: str) -> None:
        try:
            config = _load_full_config()
            config["default_theme"] = theme_class
            _save_config(config)
        except OSError as e:
            self._update_output(f"Error saving config: {escape(str(e))}", bell=True)

    def apply_theme(
        self, theme_class: str, *, silent: bool = False, save_default: bool = False
    ) -> None:
        for cls in THEME_ORDER:
            # Remove theme class from both App and Screen
            self.remove_class(cls)
            self.screen.remove_class(cls)

        # Add theme class to both App (for Toasts/Overlay) and Screen (for content)
        self.add_class(theme_class)
        self.screen.add_class(theme_class)

        self.active_theme = theme_class
        self.refresh()
        if not silent:
            self._update_output(f"Theme applied: {THEME_NAMES[theme_class]}")
        if save_default:
            self._save_theme_to_config(theme_class)

    def _apply_theme_by_name(self, theme_name: str) -> str | None:
        name = theme_name.lower()
        if name in NAME_TO_CLASS:
            key = NAME_TO_CLASS[name]
            self.apply_theme(key, save_default=False)
            return key
        if name in THEME_ORDER:
            self.apply_theme(name, save_default=False)
            return name
        matches = [k for k, v in THEME_NAMES.items() if v.lower().startswith(name)]
        if len(matches) == 1:
            self.apply_theme(matches[0], save_default=False)
            return matches[0]
        return None

    def _select_theme_and_confirm(self, theme_name_or_class: str) -> None:
        theme_class = self._apply_theme_by_name(theme_name_or_class)
        if theme_class:
            self.push_screen(
                ConfirmThemeScreen(theme_class=theme_class),
                lambda result: self._handle_confirm_callback(result, theme_class),
            )
        else:
            self._update_output(f"No theme matches: {escape(theme_name_or_class)}", bell=True)

    def _populate_menu_list(self, context: str) -> None:
        ol = self.query_one("#menu-list", OptionList)
        ol.clear_options()
        title = self.query_one("#menu-title", Static)

        items = MENUS.get(context, [])
        options = (
            self._settings_menu_options()
            if context == "settings"
            else [(item, item) for item in items]
        )

        if context == "main":
            title.update("Main Menu")
        elif context == "video":
            title.update("Video Tools")
        elif context == "audio":
            title.update("Audio Tools")
        elif context == "image":
            title.update("Image Tools")
        elif context == "cloud":
            title.update("Cloud Tools")
        elif context == "devices":
            title.update("Device Presets")
        elif context == "settings":
            title.update("Settings")
        elif context == "plugins":
            title.update("Plugins")

        for label, item_id in options:
            ol.add_option(Option(label, id=item_id))
        ol.highlighted = 0

    def _switch_to(self, view: str) -> None:
        self.screen.remove_class("themes-open")
        self.screen.remove_class("about-open")
        self.screen.remove_class("menu-open")
        self.screen.remove_class("expanded-view")

        if view == "home":
            self._update_output("")
            self.query_one(Input).focus()
        elif view == "about":
            self.screen.add_class("about-open")
            self.query_one("#about-text", Static).update(ABOUT_TEXT)
            self.query_one(Input).focus()
        elif view == "themes":
            self.screen.add_class("themes-open")
            self.screen.add_class("expanded-view")
            self._populate_themes_list()
            self._update_output("[b]Themes[/b]: Use ↑/↓ to move. Enter to select.")
            self.query_one("#themes-list", OptionList).focus()
        elif view == "menu":
            self.screen.add_class("menu-open")
            if self.menu_context != "main":
                self.screen.add_class("expanded-view")
            self._populate_menu_list(self.menu_context)
            self._update_output("")
            self.query_one("#menu-list", OptionList).focus()

    def push_view(self, view: str) -> None:
        cur = self.current_view()
        if cur and (cur != view or (cur == "menu" and view == "menu")):
            self._view_stack.append((cur, self.menu_context))
        self._switch_to(view)

    def pop_view(self) -> None:
        if self._view_stack:
            prev_view, prev_context = self._view_stack.pop()
            self.menu_context = prev_context
            self._switch_to(prev_view)
            return
        if self.current_view() == "menu" and self.menu_context != "main":
            self.menu_context = "main"
            self._switch_to("menu")
            return
        self._switch_to("home")

    def current_view(self) -> str | None:
        if self.screen.has_class("themes-open"):
            return "themes"
        if self.screen.has_class("about-open"):
            return "about"
        if self.screen.has_class("menu-open"):
            return "menu"
        return "home"

    def _update_output(self, message: str, bell: bool = False) -> None:
        self.query_one("#output-text", Static).update(message)
        if bell:
            self.bell()
        self.query_one(Input).focus()

    def _populate_themes_list(self) -> None:
        ol = self.query_one("#themes-list", OptionList)
        ol.clear_options()
        for key in THEME_ORDER:
            label_text = THEME_NAMES[key]
            label = f"• {label_text} •" if key == self.active_theme else label_text
            ol.add_option(Option(label, id=key))
        try:
            ol.highlighted = THEME_ORDER.index(self.active_theme)
        except ValueError:
            pass

    def _handle_confirm_callback(self, result: bool, theme_class: str) -> None:
        if result:
            self._save_theme_to_config(theme_class)
            msg = f"Theme applied and saved: {THEME_NAMES[theme_class]}"
        else:
            msg = f"Theme applied: {THEME_NAMES[theme_class]}"
        if self.current_view() == "themes":
            self.pop_view()
        elif self.current_view() != "home":
            self.action_go_home()
        self.query_one("#output-text", Static).update(msg)
        self.query_one(Input).clear()
        self.query_one(Input).focus()

    def _settings_menu_options(self) -> list[tuple[str, str]]:
        values = app_config._load_full_config()

        def display(key: str, empty: str = "Off") -> str:
            value = str(values.get(key, "")).strip()
            if not value:
                value = empty
            if len(value) > 32:
                value = value[:29] + "..."
            return escape(value)

        hardware = display("hw_accel")
        overwrite = (
            "On" if app_config.coerce_bool(values.get("ffmpeg_overwrite"), default=True) else "Off"
        )
        return [
            (f"yt-dlp Cookies: {display('yt_dlp_cookies')}", "yt_dlp_cookies"),
            (
                f"yt-dlp Remote Components: {display('yt_dlp_remote_components')}",
                "yt_dlp_remote_components",
            ),
            (f"Hardware Acceleration: {hardware}", "hw_accel"),
            (f"FFmpeg Overwrite: {overwrite}", "ffmpeg_overwrite"),
            (f"Whisper Model: {display('whisper_model', 'small')}", "whisper_model"),
            (f"Whisper Device: {display('whisper_device', 'auto')}", "whisper_device"),
            (f"Whisper Compute: {display('whisper_compute', 'auto')}", "whisper_compute"),
            (f"Whisper Cache Directory: {display('whisper_cache_dir')}", "whisper_cache_dir"),
        ]

    def _save_setting(self, key: str, value: object) -> bool:
        try:
            values = app_config._load_full_config()
            values[key] = value
            app_config._save_config(values)
        except OSError as error:
            self._update_output(f"Error saving setting: {escape(str(error))}", bell=True)
            return False
        return True

    def _refresh_settings_menu(self, message: str) -> None:
        self._populate_menu_list("settings")
        self._update_output(message)
        self.query_one("#menu-list", OptionList).focus()

    def _begin_setting_input(self, key: str, prompt: str) -> None:
        self.pending_setting = key
        current = str(app_config._load_full_config().get(key, ""))
        shown = current if current else "not set"
        self._update_output(f"{prompt} Current: {escape(shown)}. Enter a new value; Esc cancels.")

    def _cycle_setting(self, key: str, options: tuple[str, ...], label: str) -> None:
        current = str(app_config._load_full_config().get(key, options[0])).lower()
        try:
            next_value = options[(options.index(current) + 1) % len(options)]
        except ValueError:
            next_value = options[0]
        if not self._save_setting(key, next_value):
            return
        shown = next_value or "Off"
        self._refresh_settings_menu(f"{label}: {shown}")

    def _toggle_setting(self, key: str, label: str) -> None:
        current = app_config.coerce_bool(app_config._load_full_config().get(key), default=True)
        if not self._save_setting(key, not current):
            return
        self._refresh_settings_menu(f"{label}: {'On' if not current else 'Off'}")

    def _handle_settings_selection(self, key: str) -> None:
        if key == "yt_dlp_cookies":
            self._begin_setting_input(key, "yt-dlp cookies browser profile")
        elif key == "yt_dlp_remote_components":
            self._begin_setting_input(key, "yt-dlp remote components")
        elif key == "hw_accel":
            self._cycle_setting(key, _HW_ACCEL_OPTIONS, "Hardware acceleration")
        elif key == "ffmpeg_overwrite":
            self._toggle_setting(key, "FFmpeg overwrite")
        elif key == "whisper_model":
            self._cycle_setting(key, _WHISPER_MODEL_OPTIONS, "Whisper model")
        elif key == "whisper_device":
            self._cycle_setting(key, _WHISPER_DEVICE_OPTIONS, "Whisper device")
        elif key == "whisper_compute":
            self._cycle_setting(key, _WHISPER_COMPUTE_OPTIONS, "Whisper compute")
        elif key == "whisper_cache_dir":
            self._begin_setting_input(key, "Whisper cache directory")

    def action_go_home(self) -> None:
        self._view_stack.clear()
        self.menu_context = "main"
        self.active_tool_name = None
        self.pending_setting = None
        self._switch_to("home")

    def action_go_back(self) -> None:
        self.active_tool_name = None
        self.pending_setting = None
        self.pop_view()

    def action_show_about(self) -> None:
        if self.current_view() != "about":
            self.push_view("about")

    def action_show_menu(self) -> None:
        self.menu_context = "main"
        if self.current_view() != "menu":
            self.push_view("menu")
        else:
            self._switch_to("menu")

    def action_show_themes(self) -> None:
        if self.current_view() != "themes":
            self.push_view("themes")

    def action_show_settings(self) -> None:
        self._enter_menu("settings")

    def _enter_menu(self, context: str) -> None:
        self.menu_context = context
        if self.current_view() != "menu":
            self.push_view("menu")
        else:
            self._switch_to("menu")

    def action_show_exit(self) -> None:
        self.exit()

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            with Container(id="stage"):
                if HAS_IMAGE_LIB and os.path.exists(ICON_PATH):
                    with Center():
                        yield Image(ICON_PATH, id="logo")
                else:
                    with Center():
                        yield Static(get_ascii_art(), id="logo")
                yield Static(self.VERSION, id="version")
                yield Static(id="output-text")
                with Container(id="content-zone"):
                    yield Static(HELP_TEXT, id="help-text")
                    with Container(id="about-panel"):
                        yield Static("About CLI-Studio", id="about-title")
                        yield Static("", id="about-text")
                        yield Static("alt+b back", id="about-nav")
                    with Container(id="menu-panel"):
                        yield Static("Main Menu", id="menu-title")
                        yield OptionList(id="menu-list")
                        yield Static(
                            "↑/↓ move  •  enter select  •  esc home  •  alt+b back", id="menu-nav"
                        )
                    with Container(id="themes-panel"):
                        yield Static("Select a theme", id="themes-title")
                        yield OptionList(id="themes-list")
                        yield Static(
                            "↑/↓ move  •  enter select  •  esc home  •  alt+b back", id="themes-nav"
                        )
                yield RichLog(id="terminal-log", markup=True)
            with Container(id="input-container"):
                yield Static(">", id="prompt")
                yield Input(id="user-input", suggester=CommandSuggester())
            with Container(id="footer"):
                yield Static("[dim]enter[/dim] send", id="input-label")

    def on_mount(self) -> None:
        load_plugins(COMMAND_REGISTRY, menus=MENUS, help_registry=HELP_REGISTRY)
        self.apply_theme(self.active_theme, silent=True)
        self._switch_to("home")
        self.query_one(Input).focus()
        if not HAS_IMAGE_LIB:
            self.notify(
                "Missing 'textual-image' lib. Install with: pip install textual-image",
                severity="warning",
                timeout=5,
            )
        elif not os.path.exists(ICON_PATH):
            self.notify(f"Icon missing at {SCRIPT_DIR}", severity="warning", timeout=5)

    def push_themed_screen(self, screen_obj, callback=None):
        if hasattr(self, "active_theme"):
            screen_obj.add_class(self.active_theme)
        self.push_screen(screen_obj, callback)

    def _open_tool(self, selected: str) -> None:
        self.active_tool_name = selected.lower()
        response = CommandHandler.handle_command(selected)
        if isinstance(response, Screen):
            self.push_themed_screen(response)
        else:
            self._update_output(str(response))

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "themes-list":
            theme_class = str(event.option.id)
            self.apply_theme(theme_class, save_default=False)
            self.push_screen(
                ConfirmThemeScreen(theme_class=theme_class),
                lambda result: self._handle_confirm_callback(result, theme_class),
            )
            return

        if event.option_list.id == "menu-list":
            selected = str(event.option.id)
            if self.menu_context == "main":
                if selected == "Video Tools":
                    self.menu_context = "video"
                    self._switch_to("menu")
                elif selected == "Audio Tools":
                    self.menu_context = "audio"
                    self._switch_to("menu")
                elif selected == "Image Tools":
                    self.menu_context = "image"
                    self._switch_to("menu")
                elif selected == "Cloud Tools":
                    self.menu_context = "cloud"
                    self._switch_to("menu")
                elif selected == "Device Presets":
                    self.menu_context = "devices"
                    self._switch_to("menu")
                elif selected == "Plugins":
                    self.menu_context = "plugins"
                    self._switch_to("menu")
                elif selected == "Settings":
                    self.action_show_settings()
                elif selected.lower() in COMMAND_REGISTRY:
                    self._open_tool(selected)
            else:
                if self.menu_context == "settings":
                    self._handle_settings_selection(selected)
                else:
                    self._open_tool(selected)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "user-input":
            return

        raw_value = event.value
        value = raw_value.strip()
        self.query_one(Input).clear()
        if self.pending_setting is not None:
            key = self.pending_setting
            self.pending_setting = None
            if key == "whisper_cache_dir":
                if not value:
                    value = str(app_config.DEFAULT_CONFIG["whisper_cache_dir"])
                else:
                    try:
                        value = app_config.validate_cache_dir(value)
                    except ValueError as err:
                        self.notify(str(err), severity="error")
                        self.pending_setting = key
                        return
            if self._save_setting(key, value):
                self._refresh_settings_menu("Setting saved.")
            else:
                self.pending_setting = key
            return
        if not value:
            return
        self.query_one("#output-text", Static).update("")
        cmd = value.lower()

        handler = _COMMANDS.get(cmd)
        if handler:
            handler(self)
            return

        if cmd.startswith("/themes/"):
            name = value[len("/themes/") :].strip()
            if name:
                self._select_theme_and_confirm(name)
            else:
                self._update_output("Usage: /themes/<name>", bell=True)
            return
        if self.current_view() == "themes" and value:
            self._select_theme_and_confirm(value)
            return
        _, fail = log_palette_colors(self.active_theme)
        self._update_output(f"[bold {fail}]Unknown command:[/bold {fail}] {escape(cmd)}", bell=True)

    def on_unmount(self) -> None:
        try:
            from ui.progress import cleanup_active_process_groups

            cleanup_active_process_groups()
        except Exception:
            pass


def main() -> None:
    app = CliStudioApp()
    app.run()


if __name__ == "__main__":
    main()
