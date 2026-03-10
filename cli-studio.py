#!/usr/bin/env python3
import os
import sys
import json
from textual.app import App, ComposeResult
from textual.screen import ModalScreen, Screen
from textual.widgets import Static, Input, OptionList, RichLog
from textual.widgets.option_list import Option
from textual.containers import Container, Center
from textual.suggester import Suggester

try:
    from textual_image.widget import Image
    HAS_IMAGE_LIB = True
except ImportError:
    HAS_IMAGE_LIB = False
    Image = None

from studio_themes import (
    LAYOUT_CSS,
    THEMES_CSS,
    THEME_ORDER,
    THEME_NAMES,
    NAME_TO_CLASS,
)

from config import MENUS, get_help
from workflows.registry import CommandHandler

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
/log          toggle debug log     ctrl+l
/back         go back              alt+b
/exit         exit the app         alt+e"""

ABOUT_TEXT = (
    "CLI ▶ Studio is a terminal user interface for image, video, and audio manipulation.\n"
    "It simplifies the use of command-line media tools by providing an intuitive, menu-driven workflow,\n"
    "allowing beginners to access core features without memorizing complex commands."
)

CONFIG_FILE = os.path.expanduser("~/.cli_studio_config.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_FILENAME = "cli-studio_icon.png"
ICON_PATH = os.path.join(SCRIPT_DIR, ICON_FILENAME)

def get_ascii_art() -> str:
    lines = ASCII_ART.strip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)

class HelpModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
    def __init__(self, title: str, body: str):
        super().__init__()
        self.title = title
        self.body = body

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
        self.screen.add_class(self.app.active_theme)

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
    COMMANDS = ["/home", "/back", "/about", "/menu", "/themes", "/exit", "/video", "/audio", "/image"]
    async def get_suggestion(self, value: str) -> str | None:
        if not value.startswith("/"): return None
        if value.startswith("/themes/"):
            prefix = "/themes/"
            part = value[len(prefix) :]
            if not part: return f"{prefix}{THEME_NAMES[THEME_ORDER[0]]}"
            for name in THEME_NAMES.values():
                if name.startswith(part): return f"{prefix}{name}"
            for cls in THEME_ORDER:
                if cls.startswith(part): return f"{prefix}{cls}"
            return None
        for c in self.COMMANDS:
            if c.startswith(value): return c
        return None

class CliStudioApp(App):
    TITLE = "CLI-Studio"
    VERSION = "v0.1.0"
    CSS = LAYOUT_CSS + THEMES_CSS
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "toggle_log", "Toggle Log"),
        ("escape", "go_home", "Home"),
        ("alt+a", "show_about", "About"),
        ("alt+m", "show_menu", "Menu"),
        ("alt+t", "show_themes", "Themes"),
        ("alt+b", "go_back", "Back"),
        ("alt+e", "show_exit", "Exit"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_theme = self._load_theme_from_config()
        self.view_stack: list[str] = []
        self.menu_context = "main"
        self.active_tool_name = None

    def action_toggle_log(self) -> None:
        if self.screen.has_class("log-open"):
            self.screen.remove_class("log-open")
        else:
            self.screen.add_class("log-open")

    def action_show_help(self) -> None:
        if self.active_tool_name:
            self.push_screen(HelpModal(self.active_tool_name.title(), get_help(self.active_tool_name)))
        elif self.current_view() == "menu" and self.menu_context != "main":
            try:
                ol = self.query_one("#menu-list", OptionList)
                if ol.highlighted is not None:
                    opt = ol.get_option_at_index(ol.highlighted)
                    self.push_screen(HelpModal(str(opt.id).title(), get_help(str(opt.id).lower())))
            except: pass


    def _load_theme_from_config(self) -> str:
        default = "t-default"
        if not os.path.exists(CONFIG_FILE): return default
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            theme = data.get("default_theme")
            if theme in THEME_ORDER: return theme
            return default
        except: return default

    def _save_theme_to_config(self, theme_class: str) -> None:
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"default_theme": theme_class}, f, indent=2)
        except IOError as e:
            self._update_output(f"Error saving config: {e}", bell=True)

    def apply_theme(self, theme_class: str, *, silent: bool = False, save_default: bool = False) -> None:
        for cls in THEME_ORDER:
            # Remove theme class from both App and Screen
            self.remove_class(cls)
            self.screen.remove_class(cls)
            
        # Add theme class to both App (for Toasts/Overlay) and Screen (for content)
        self.add_class(theme_class)
        self.screen.add_class(theme_class)
        
        self.active_theme = theme_class
        self.refresh()
        if not silent: self._update_output(f"Theme applied: {THEME_NAMES[theme_class]}")
        if save_default: self._save_theme_to_config(theme_class)

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
            self._update_output(f"No theme matches: {theme_name_or_class}", bell=True)

    def _populate_menu_list(self, context: str) -> None:
        ol = self.query_one("#menu-list", OptionList)
        ol.clear_options()
        title = self.query_one("#menu-title", Static)
        
        items = MENUS.get(context, [])

        if context == "main": title.update("Main Menu")
        elif context == "video": title.update("Video Tools")
        elif context == "audio": title.update("Audio Tools")
        elif context == "image": title.update("Image Tools")
            
        for item in items:
            ol.add_option(Option(item, id=item))
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
            self.query_one("#themes-list", OptionList).focus()
            self._update_output("[b]Themes[/b]: Use ↑/↓ to move. Enter to select.")
        elif view == "menu":
            self.screen.add_class("menu-open")
            if self.menu_context != "main":
                self.screen.add_class("expanded-view")
            self._populate_menu_list(self.menu_context)
            self.query_one("#menu-list", OptionList).focus()
            self._update_output("")

    def push_view(self, view: str) -> None:
        cur = self.current_view()
        if cur: self.view_stack.append(cur)
        self._switch_to(view)

    def pop_view(self) -> None:
        if self.current_view() == "menu" and self.menu_context != "main":
            self.menu_context = "main"
            self._switch_to("menu")
            return
        if self.view_stack:
            prev = self.view_stack.pop()
            if prev == "menu": self.menu_context = "main"
            self._switch_to(prev)
        else:
            self._switch_to("home")

    def current_view(self) -> str | None:
        if self.screen.has_class("themes-open"): return "themes"
        if self.screen.has_class("about-open"): return "about"
        if self.screen.has_class("menu-open"): return "menu"
        return "home"

    def _update_output(self, message: str, bell: bool = False) -> None:
        self.query_one("#output-text").update(message)
        if bell: self.bell()
        self.query_one(Input).focus()

    def _populate_themes_list(self) -> None:
        ol = self.query_one("#themes-list", OptionList)
        ol.clear_options()
        for key in THEME_ORDER:
            label_text = THEME_NAMES[key]
            label = f"• {label_text} •" if key == self.active_theme else label_text
            ol.add_option(Option(label, id=key))
        try: ol.index = THEME_ORDER.index(self.active_theme)
        except ValueError: pass

    def _handle_confirm_callback(self, result: bool, theme_class: str) -> None:
        if result:
            self._save_theme_to_config(theme_class)
            msg = f"Theme applied and saved: {THEME_NAMES[theme_class]}"
        else:
            msg = f"Theme applied: {THEME_NAMES[theme_class]}"
        if self.current_view() == "themes": self.pop_view()
        elif self.current_view() != "home": self.action_go_home()
        self.query_one("#output-text").update(msg)
        self.query_one(Input).clear()
        self.query_one(Input).focus()

    def action_go_home(self) -> None:
        self.view_stack.clear()
        self.menu_context = "main"
        self.active_tool_name = None
        self._switch_to("home")
    def action_go_back(self) -> None: 
        self.active_tool_name = None
        self.pop_view()
    def action_show_about(self) -> None:
        if self.current_view() != "about": self.push_view("about")
    def action_show_menu(self) -> None:
        self.menu_context = "main"
        if self.current_view() != "menu": self.push_view("menu")
        else: self._switch_to("menu")
    def action_show_themes(self) -> None:
        if self.current_view() != "themes": self.push_view("themes")
    def action_show_exit(self) -> None: self.exit()

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            with Container(id="stage"):
                if HAS_IMAGE_LIB and os.path.exists(ICON_PATH):
                    with Center(): yield Image(ICON_PATH, id="logo")
                else:
                    with Center(): yield Static(get_ascii_art(), id="logo")
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
                        yield Static("↑/↓ move  •  enter select  •  esc home  •  alt+b back", id="menu-nav")
                    with Container(id="themes-panel"):
                        yield Static("Select a theme", id="themes-title")
                        yield OptionList(id="themes-list")
                        yield Static("↑/↓ move  •  enter select  •  esc home  •  alt+b back", id="themes-nav")
                yield RichLog(id="terminal-log", markup=True)
            with Container(id="input-container"):
                yield Static(">", id="prompt")
                yield Input(id="user-input", suggester=CommandSuggester())
            with Container(id="footer"):
                yield Static("[dim]enter[/dim] send", id="input-label")

    def on_mount(self) -> None:
        self.apply_theme(self.active_theme, silent=True)
        self._switch_to("home")
        self.query_one(Input).focus()
        if not HAS_IMAGE_LIB: self.notify("Missing 'textual-image' lib.", severity="warning", timeout=5)
        elif not os.path.exists(ICON_PATH): self.notify(f"Icon missing at {SCRIPT_DIR}", severity="warning", timeout=5)

    def push_themed_screen(self, screen_obj, callback=None):
        if hasattr(self, "active_theme"):
            screen_obj.add_class(self.active_theme)
        self.push_screen(screen_obj, callback)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "themes-list":
            theme_class = event.option.id
            self.apply_theme(theme_class, save_default=False)
            self.push_screen(
                ConfirmThemeScreen(theme_class=theme_class),
                lambda result: self._handle_confirm_callback(result, theme_class),
            )
            return

        if event.option_list.id == "menu-list":
            selected = event.option.id
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
            else:
                self.active_tool_name = selected.lower()
                response = CommandHandler.handle_command(selected)
                if isinstance(response, Screen):
                    self.push_themed_screen(response)
                else:
                    self._update_output(str(response))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "user-input": return

        value = event.value.strip()
        self.query_one(Input).clear()
        if not value: return
        self.query_one("#output-text").update("")
        cmd = value.lower()

        if cmd == "/home": self.action_go_home(); return
        if cmd == "/back": self.action_go_back(); return
        if cmd == "/about": self.action_show_about(); return
        if cmd == "/menu": self.action_show_menu(); return
        if cmd == "/video":
            self.menu_context = "video"
            if self.current_view() != "menu": self.push_view("menu")
            else: self._switch_to("menu")
            return
        if cmd == "/audio":
            self.menu_context = "audio"
            if self.current_view() != "menu": self.push_view("menu")
            else: self._switch_to("menu")
            return
        if cmd == "/image":
            self.menu_context = "image"
            if self.current_view() != "menu": self.push_view("menu")
            else: self._switch_to("menu")
            return
        if cmd == "/themes": self.action_show_themes(); return
        if cmd == "/exit": self.action_show_exit(); return

        if cmd.startswith("/themes/"):
            name = value[len("/themes/") :].strip()
            if name: self._select_theme_and_confirm(name)
            else: self._update_output("Usage: /themes/<name>", bell=True)
            return
        if self.current_view() == "themes" and value:
            self._select_theme_and_confirm(value)
            return
        self._update_output(f"[bold #f7768e]Unknown command:[/bold #f7768e] {cmd}", bell=True)

if __name__ == "__main__":
    app = CliStudioApp()
    app.run()
