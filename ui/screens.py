import logging
import os

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import DirectoryTree, Input, Label, OptionList
from textual.widgets.option_list import Option

logger = logging.getLogger(__name__)


class _BaseInputModal(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        prompt: str,
        default_val: str,
        state: dict,
        next_step_func,
        allow_empty: bool = False,
    ):
        super().__init__()
        self.prompt = prompt
        self.default_val = default_val
        self.state = state
        self.next_step_func = next_step_func
        self.allow_empty = allow_empty

    def action_cancel(self):
        self.dismiss()

    def _submit(self, value: str) -> None:
        val = (value or "").strip() or self.default_val
        if not val and not self.allow_empty:
            self.app.notify("Input cannot be empty", severity="error")
            return
        try:
            next_screen = self.next_step_func(val, self.state)
        except ValueError as exc:
            msg = str(exc).strip()
            if not msg or msg.startswith("invalid literal") or msg.startswith("could not convert"):
                self.app.notify("Invalid input. Check the format and try again.", severity="error")
            else:
                self.app.notify(f"Invalid input: {msg}", severity="error")
            return
        except FileNotFoundError as exc:
            name = exc.filename or "the file"
            self.app.notify(f"File not found: {name}", severity="error")
            return
        except OSError as exc:
            self.app.notify(f"File system error: {exc.strerror or exc}", severity="error")
            return
        except Exception as exc:
            self.app.notify("Unexpected error; press '?' for help.", severity="error")
            logger.exception("Wizard step %s raised: %s", self.prompt, exc)
            return
        if next_screen is None:
            self.app.notify(
                "Nothing to run for that selection (blocked, empty, or cancelled).",
                severity="warning",
            )
            self.dismiss()
            return
        self.dismiss()
        if next_screen:
            self.app.push_themed_screen(next_screen)  # type: ignore[attr-defined]  # added dynamically on CliStudioApp


class TextInputScreen(_BaseInputModal):
    def __init__(
        self,
        prompt: str,
        placeholder: str,
        default_val: str,
        state: dict,
        next_step_func,
        allow_empty: bool = False,
    ):
        super().__init__(prompt, default_val, state, next_step_func, allow_empty=allow_empty)
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.prompt, id="input-label")
            yield Input(value=self.default_val, placeholder=self.placeholder, id="path-input")
            yield Label("Enter to Confirm • Esc to Cancel", id="input-sublabel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)


class FilePickerScreen(_BaseInputModal):
    def __init__(self, prompt: str, default_val: str, state: dict, next_step_func):
        super().__init__(prompt, default_val or os.path.expanduser("~"), state, next_step_func)

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.prompt, id="input-label")
            yield Input(value=self.default_val, id="path-input")
            yield DirectoryTree(os.path.expanduser("~"), id="dir-tree")
            yield Label("Select File/Dir • Enter to Confirm • Esc Cancel", id="input-sublabel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        try:
            dt = self.query_one("#dir-tree")
            dt.styles.height = 10
            dt.styles.border = ("solid", "#888888")
            dt.styles.margin = (1, 0)
            dt.styles.overflow_x = "hidden"
        except Exception:
            pass

    def on_directory_tree_file_selected(self, event):
        self.query_one(Input).value = str(event.path)
        self.query_one(Input).focus()

    def on_directory_tree_directory_selected(self, event):
        self.query_one(Input).value = str(event.path)
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)


class OptionSelectScreen(_BaseInputModal):
    def __init__(self, prompt: str, options: list, state: dict, next_step_func):
        super().__init__(prompt, "", state, next_step_func)
        self.options_list = options

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.prompt, id="input-label")
            yield OptionList(*[Option(o, id=o) for o in self.options_list], id="format-options")
            yield Label("Enter to Select • Esc to Cancel", id="input-sublabel")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._submit(str(event.option.id))
