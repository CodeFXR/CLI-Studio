import os
from textual.screen import ModalScreen
from textual.widgets import Label, Input, OptionList, DirectoryTree
from textual.widgets.option_list import Option
from textual.containers import Container
from textual.app import ComposeResult

class TextInputScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str, placeholder: str, default_val: str, state: dict, next_step_func):
        super().__init__()
        self.prompt = prompt
        self.placeholder = placeholder
        self.default_val = default_val
        self.state = state
        self.next_step_func = next_step_func

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.prompt, id="input-label")
            yield Input(value=self.default_val, placeholder=self.placeholder, id="path-input")
            yield Label("Enter to Confirm • Esc to Cancel", id="input-sublabel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def action_cancel(self):
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip() or self.default_val
        if not val:
            self.app.notify("Input cannot be empty", severity="error")
            return
        try:
            next_screen = self.next_step_func(val, self.state)
            self.dismiss()
            if next_screen:
                self.app.push_themed_screen(next_screen)
        except Exception as e:
            self.app.notify(str(e), severity="error")


class FilePickerScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str, default_val: str, state: dict, next_step_func):
        super().__init__()
        self.prompt = prompt
        self.default_val = default_val or os.path.expanduser("~")
        self.state = state
        self.next_step_func = next_step_func

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
        except: pass

    def on_directory_tree_file_selected(self, event):
        self.query_one(Input).value = str(event.path)
        self.query_one(Input).focus()

    def on_directory_tree_directory_selected(self, event):
        self.query_one(Input).value = str(event.path)
        self.query_one(Input).focus()

    def action_cancel(self):
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip() or self.default_val
        if not val:
            self.app.notify("Input cannot be empty", severity="error")
            return
        try:
            next_screen = self.next_step_func(val, self.state)
            self.dismiss()
            if next_screen:
                self.app.push_themed_screen(next_screen)
        except Exception as e:
            self.app.notify(str(e), severity="error")


class OptionSelectScreen(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str, options: list, state: dict, next_step_func):
        super().__init__()
        self.prompt = prompt
        self.options_list = options
        self.state = state
        self.next_step_func = next_step_func

    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label(self.prompt, id="input-label")
            yield OptionList(*[Option(o, id=o) for o in self.options_list], id="format-options")
            yield Label("Enter to Select • Esc to Cancel", id="input-sublabel")

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def action_cancel(self):
        self.dismiss()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        val = event.option.id
        try:
            next_screen = self.next_step_func(val, self.state)
            self.dismiss()
            if next_screen:
                self.app.push_themed_screen(next_screen)
        except Exception as e:
            self.app.notify(str(e), severity="error")