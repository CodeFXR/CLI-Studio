import os
import subprocess

from config import validate_remote_name
from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label
from textual.worker import get_current_worker

from ui.progress import GenericCliProgressScreen, _LoggingModalScreen
from ui.screens import FilePickerScreen, TextInputScreen


def build_rclone_copy_flow():
    def step2(local_path, state):
        state["local_path"] = local_path
        return TextInputScreen(
            "Remote name (as configured in `rclone config`):",
            "myremote",
            "",
            state,
            step3,
        )

    def step3(remote_name, state):
        state["remote_name"] = validate_remote_name(remote_name)
        return TextInputScreen(
            "Remote path (after the colon):",
            "backups/folder",
            "",
            state,
            step4,
        )

    def step4(remote_path, state):
        state["remote_path"] = remote_path
        expanded_local = os.path.abspath(os.path.expanduser(state["local_path"]))
        cmd = [
            "rclone",
            "copy",
            expanded_local,
            f"{state['remote_name']}:{state['remote_path']}",
        ]
        return GenericCliProgressScreen(cmd, "rclone", expanded_local)

    return FilePickerScreen("Select Local File/Folder to upload:", "", {}, step2)


class _RcloneListRemotesScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, target: str) -> None:
        super().__init__()
        self.target = target

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Listing Rclone Remotes...", id="task-label")
            yield Label(f"Saving to: {escape(self.target)}", id="status-label")

    def on_mount(self) -> None:
        self.run_worker(self._run, exclusive=True, thread=True)

    def _run(self) -> None:
        worker = get_current_worker()
        target_dir = os.path.dirname(self.target)
        if target_dir:
            try:
                os.makedirs(target_dir, exist_ok=True)
            except OSError:
                pass
        try:
            result = subprocess.run(
                ["rclone", "listremotes", "--long"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            self.app.call_from_thread(
                self.app.notify,
                "rclone not found. Please install it.",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(
                self.app.notify,
                "rclone listremotes timed out.",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        if worker.is_cancelled:
            self.app.call_from_thread(self.safe_dismiss)
            return
        if result.returncode != 0:
            detail = result.stderr.strip() or "rclone listremotes failed"
            self.app.call_from_thread(
                self.app.notify,
                f"rclone failed: {escape(detail)}",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        if os.path.islink(self.target):
            self.app.call_from_thread(
                self.app.notify,
                f"Target cannot be a symlink: {escape(self.target)}",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(self.target, flags, 0o644)
            with open(fd, "w", encoding="utf-8") as handle:
                handle.write(result.stdout)
        except OSError as exc:
            self.app.call_from_thread(
                self.app.notify,
                f"Could not write {escape(self.target)}: {escape(str(exc))}",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        self.app.call_from_thread(
            self.write_log,
            self._log_msg("saved", escape(result.stdout.strip() or "(no remotes)")),
        )
        self.app.call_from_thread(
            self.app.notify,
            f"Saved remotes list to {self.target}",
            severity="information",
        )
        self.app.call_from_thread(self.safe_dismiss)


def build_rclone_list_remotes_flow():
    def step2(out_dir, state):
        state["out_dir"] = out_dir
        expanded_out_dir = os.path.abspath(os.path.expanduser(out_dir))
        target = os.path.join(expanded_out_dir, "rclone_remotes.txt")
        return _RcloneListRemotesScreen(target)

    return FilePickerScreen("Save remotes list to (directory):", os.path.expanduser("~"), {}, step2)
