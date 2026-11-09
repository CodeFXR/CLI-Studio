import os
import shutil
import subprocess
import tempfile
import threading
from typing import cast

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, Static
from textual.worker import get_current_worker

from ui.progress import _kill_process_group, _register_process_group, _unregister_process_group
from workflows.backends import ChafaBackend, get_backend


class PreviewModalScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, input_path: str, preview_type: str) -> None:
        super().__init__()
        self.input_path = input_path
        self.preview_type = preview_type
        self.process: subprocess.Popen | None = None
        self._cancelled = False

    def compose(self) -> ComposeResult:
        title = "Image Preview" if self.preview_type == "image" else "Audio Waveform Preview"
        with Container(id="preview-dialog"):
            yield Label(title, id="preview-title")
            yield Static("Preparing preview...", id="preview-content", markup=False)
            yield Label(f"{escape(self.input_path)}\nEsc to close", id="preview-help")

    def on_mount(self) -> None:
        self.run_worker(self.run_preview, exclusive=True, thread=True)

    def action_close(self) -> None:
        self._cancelled = True
        proc = self.process
        if proc:
            threading.Thread(
                target=_kill_process_group,
                args=(proc,),
                daemon=True,
                name="preview-killer",
            ).start()
        try:
            self.dismiss()
        except Exception:
            pass

    def _kill_process(self) -> None:
        proc = self.process
        if proc:
            _kill_process_group(proc)

    def _run_cmd(self, cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if self._cancelled:
            raise RuntimeError("Preview cancelled")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        self.process = proc
        _register_process_group(proc.pid)
        try:
            if self._cancelled:
                _kill_process_group(proc)
                raise RuntimeError("Preview cancelled")
            stdout, stderr = proc.communicate(timeout=timeout)
            return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            _kill_process_group(proc)
            raise
        except Exception:
            _kill_process_group(proc)
            raise
        finally:
            if proc:
                _unregister_process_group(proc.pid)
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                if proc.stderr:
                    try:
                        proc.stderr.close()
                    except Exception:
                        pass
            self.process = None

    def _show_content(self, output: str, status: str) -> None:
        try:
            self.query_one("#preview-content", Static).update(Text.from_ansi(output))
            self.query_one("#preview-help", Label).update(escape(f"{status}\nEsc to close"))
        except Exception:
            pass

    def _show_error(self, message: str) -> None:
        try:
            self.query_one("#preview-content", Static).update(escape(message))
            self.query_one("#preview-help", Label).update("Esc to close")
        except Exception:
            pass
        try:
            self.app.notify(escape(message), severity="warning")
        except Exception:
            pass

    def _render_preview(self, image_path: str) -> tuple[str, str]:
        backend = cast(ChafaBackend, get_backend("chafa"))
        command = backend.build_render_command(image_path, width=76, height=20)
        result = self._run_cmd(command, timeout=30)
        if result.returncode != 0:
            detail = result.stderr.strip() or "chafa could not render this file"
            raise RuntimeError(detail)
        return result.stdout, "Preview ready"

    def _build_waveform(self, input_path: str, output_path: str) -> None:
        backend = cast(ChafaBackend, get_backend("chafa"))
        if shutil.which("audiowaveform"):
            command = backend.build_audiowaveform_command(input_path, output_path)
            result = self._run_cmd(command, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                return
        command = backend.build_waveform_command(input_path, output_path)
        result = self._run_cmd(command, timeout=120)
        if result.returncode != 0:
            detail = result.stderr.strip() or "ffmpeg could not create a waveform"
            raise RuntimeError(detail)

    def run_preview(self) -> None:
        worker = get_current_worker()
        expanded_path = os.path.abspath(os.path.expanduser(self.input_path))
        if worker.is_cancelled:
            return
        if not os.path.exists(expanded_path):
            self.app.call_from_thread(self._show_error, "Preview input was not found.")
            return

        try:
            if self.preview_type == "image":
                output, status = self._render_preview(expanded_path)
            else:
                with tempfile.TemporaryDirectory(prefix="cli-studio-waveform-") as temp_dir:
                    waveform_path = os.path.join(temp_dir, "waveform.png")
                    self._build_waveform(expanded_path, waveform_path)
                    output, status = self._render_preview(waveform_path)
            if not output.strip():
                raise RuntimeError("Preview returned no output")
            self.app.call_from_thread(self._show_content, output, status)
        except FileNotFoundError as error:
            executable = str(error.filename or "required preview tool")
            self.app.call_from_thread(
                self._show_error,
                f"{executable} is not installed.",
            )
        except subprocess.TimeoutExpired:
            self.app.call_from_thread(self._show_error, "Preview timed out.")
        except Exception as error:
            self.app.call_from_thread(self._show_error, f"Preview failed: {error}")


PreviewScreen = PreviewModalScreen
