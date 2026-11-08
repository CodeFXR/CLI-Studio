import os
import re
import signal
import subprocess
from typing import Any, cast

import config
from natsort import natsorted
from PIL import Image
from rich.markup import escape
from studio_themes import log_palette_colors
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ProgressBar
from textual.worker import get_current_worker

from workflows.backends import PillowBackend, YtDlpBackend, get_backend
from workflows.utils import unique_path


def _ffmpeg_overwrite_flag() -> str:
    overwrite = config.coerce_bool(
        config._load_full_config().get("ffmpeg_overwrite"),
        default=True,
    )
    return "-y" if overwrite else "-n"


class _LoggingModalScreen(ModalScreen[Any]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dismissed = False
        self._cancelled = False
        self._app_override = None

    @property
    def app(self) -> Any:
        try:
            return getattr(self, "_app_override", None) or super().app
        except Exception:
            return getattr(self, "_app_override", None)

    @app.setter
    def app(self, value: Any) -> None:
        self._app_override = value

    def safe_dismiss(self):
        if not getattr(self, "_dismissed", False):
            self._dismissed = True
            try:
                self.dismiss()
            except Exception:
                pass

    def _kill_process_group(self, proc: subprocess.Popen | None):
        if not proc:
            return
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
        except (ProcessLookupError, OSError):
            try:
                proc.terminate()
            except Exception:
                pass

    def write_log(self, text):
        try:
            log = cast(Any, self.app.query_one("#terminal-log"))
            log.write(text)
        except Exception:
            try:
                log = cast(Any, self.app.query_one("#terminal-log"))
                log.write(escape(str(text)))
            except Exception:
                pass

    def _log_msg(self, kind: str, body: str) -> str:
        """Build a '[bold COLOR]Kind:[/bold COLOR] body' line in the active theme's palette."""
        app = getattr(self, "app", None)
        theme = getattr(app, "active_theme", None)
        accent, fail = log_palette_colors(theme) if theme else ("#00dadf", "#f7768e")
        color = accent if kind == "executing" else fail
        return f"[bold {color}]{kind.title()}:[/bold {color}] {body}"


class DownloadProgressScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "cancel_download", "Cancel")]

    def __init__(
        self,
        url: str,
        save_path: str,
        cookies: str = "",
        remote_components: str = "",
        is_audio: bool = False,
        is_playlist: bool = False,
    ):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.cookies = cookies
        self.remote_components = remote_components
        self.is_audio = is_audio
        self.is_playlist = is_playlist
        self.process: subprocess.Popen[Any] | None = None
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Downloading Media...", id="task-label")
            yield ProgressBar(total=100, show_eta=True)
            yield Label(f"Saving to: {escape(self.save_path)}", id="status-label")

    def on_mount(self) -> None:
        self.progress_bar = self.query_one(ProgressBar)
        self.run_worker(self.run_ytdlp, exclusive=True, thread=True)

    def action_cancel_download(self):
        self._cancelled = True
        if self.process:
            self._kill_process_group(self.process)
        self.safe_dismiss()
        self.app.notify("Download Cancelled", severity="warning")

    def run_ytdlp(self):
        worker = get_current_worker()
        bar = self.progress_bar

        expanded_path = os.path.abspath(os.path.expanduser(self.save_path))
        if not os.path.exists(expanded_path):
            try:
                os.makedirs(expanded_path)
            except OSError:
                self.app.call_from_thread(self.app.notify, "Invalid Path", severity="error")
                self.app.call_from_thread(self.safe_dismiss)
                return

        if not self.is_playlist and ("list=" in self.url or "playlist?" in self.url):
            self.app.call_from_thread(
                self.app.notify,
                "URL looks like a playlist. Use 'Download Playlist' for full downloads. Downloading first video only.",
                severity="warning",
            )

        backend = cast(YtDlpBackend, get_backend("yt-dlp"))
        cmd = backend.build_command(
            self.url,
            expanded_path,
            cookies=self.cookies,
            remote_components=self.remote_components,
            is_audio=self.is_audio,
            is_playlist=self.is_playlist,
        )

        if self._cancelled or worker.is_cancelled:
            self.app.call_from_thread(self.safe_dismiss)
            return

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except FileNotFoundError:
            self.app.call_from_thread(
                self.app.notify, "yt-dlp not found. Please install it.", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        percent_re = re.compile(r"(\d{1,3}\.\d)%")

        proc = self.process
        if proc and proc.stdout:
            for line in proc.stdout:
                self.app.call_from_thread(self.write_log, escape(line.strip()))
                if worker.is_cancelled or self._cancelled:
                    self._kill_process_group(proc)
                    break

                match = percent_re.search(line)
                if match:
                    try:
                        p = float(match.group(1))
                        if bar:
                            self.app.call_from_thread(bar.update, progress=p)
                    except ValueError:
                        pass

            proc.wait()
            if proc.returncode == 0:
                self.app.call_from_thread(self.app.notify, "Download Complete!", severity="information")
            elif proc.returncode != -15:
                self.app.call_from_thread(self.app.notify, "Download Failed.", severity="error")

        self.app.call_from_thread(self.safe_dismiss)


class FfmpegProgressScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(
        self, input_file: str, output_file: str, action_args: list, target_ext: str = None
    ):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.action_args = action_args
        self.target_ext = target_ext
        self.process: subprocess.Popen[Any] | None = None
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Processing Media (FFmpeg)...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Output: {escape(self.output_file)}", id="status-label")

    def on_mount(self) -> None:
        self.progress_bar = self.query_one(ProgressBar)
        self.run_worker(self.run_ffmpeg, exclusive=True, thread=True)

    def action_cancel_process(self):
        self._cancelled = True
        if self.process:
            self._kill_process_group(self.process)
        self.safe_dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_ffmpeg(self):
        worker = get_current_worker()
        expanded_in = os.path.abspath(os.path.expanduser(self.input_file))
        expanded_out = os.path.abspath(os.path.expanduser(self.output_file))
        overwrite_flag = _ffmpeg_overwrite_flag()

        if os.path.isdir(expanded_in):
            if os.path.isfile(expanded_out):
                self.app.call_from_thread(
                    self.app.notify,
                    f"Output path '{escape(expanded_out)}' is a file, not a directory.",
                    severity="error",
                )
                self.app.call_from_thread(self.safe_dismiss)
                return
            try:
                os.makedirs(expanded_out, exist_ok=True)
            except OSError as e:
                self.app.call_from_thread(
                    self.app.notify, f"Could not create output directory: {escape(str(e))}", severity="error"
                )
                self.app.call_from_thread(self.safe_dismiss)
                return

            common_media_exts = {
                ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg",
                ".3gp", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus", ".m4a", ".wma", ".aiff",
            }
            all_files = [
                f for f in os.listdir(expanded_in) if os.path.isfile(os.path.join(expanded_in, f))
            ]
            all_files = [f for f in all_files if not f.startswith(".")]
            media_files = [f for f in all_files if os.path.splitext(f)[1].lower() in common_media_exts]
            files = media_files if media_files else all_files

            bar = self.progress_bar
            if bar:
                self.app.call_from_thread(bar.update, total=len(files), progress=0)

            failures = []
            for idx, f in enumerate(files):
                if self._cancelled or worker.is_cancelled:
                    break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith("."):
                    ext = "." + ext
                out_f = unique_path(expanded_out, os.path.splitext(f)[0], ext)

                cmd = ["ffmpeg", overwrite_flag, "-i", in_f] + self.action_args + [out_f]
                try:
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )
                    _, stderr = self.process.communicate()
                    rc = self.process.returncode
                except Exception:
                    rc = 1
                finally:
                    self.process = None

                if rc != 0 and rc != -15 and not self._cancelled:
                    failures.append(f)
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(f)} (exit {rc})"),
                    )
                if bar:
                    self.app.call_from_thread(bar.update, progress=idx + 1)

            if self._cancelled or worker.is_cancelled:
                self.app.call_from_thread(
                    self.app.notify, "Batch Processing Cancelled", severity="warning"
                )
            elif failures:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Batch done. {len(failures)} of {len(files)} failed (see log).",
                    severity="warning",
                )
            else:
                self.app.call_from_thread(
                    self.app.notify, "Batch Processing Complete!", severity="information"
                )
            self.app.call_from_thread(self.safe_dismiss)
            return

        if not os.path.exists(expanded_in):
            self.app.call_from_thread(self.app.notify, "Input file not found.", severity="error")
            self.app.call_from_thread(self.safe_dismiss)
            return

        if self._cancelled or worker.is_cancelled:
            self.app.call_from_thread(self.safe_dismiss)
            return

        out_dir = os.path.dirname(expanded_out)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except OSError:
                pass

        cmd = ["ffmpeg", overwrite_flag, "-i", expanded_in] + self.action_args + [expanded_out]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            self.app.call_from_thread(
                self.write_log, self._log_msg("executing", escape(" ".join(cmd)))
            )
        except FileNotFoundError:
            self.app.call_from_thread(
                self.app.notify, "ffmpeg not found. Please install it.", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        proc = self.process
        if proc and proc.stdout:
            for line in proc.stdout:
                self.app.call_from_thread(self.write_log, escape(line.strip()))
                if worker.is_cancelled or self._cancelled:
                    self._kill_process_group(proc)
                    break

            proc.wait()
            if proc.returncode == 0:
                self.app.call_from_thread(
                    self.app.notify, "Processing Complete!", severity="information"
                )
            elif proc.returncode != -15:
                self.app.call_from_thread(self.app.notify, "Processing Failed.", severity="error")

        self.app.call_from_thread(self.safe_dismiss)


class GenericCliProgressScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(self, cmds, tool_name: str, target: str, out_file: str | None = None):
        super().__init__()
        if cmds and isinstance(cmds[0], (str, bytes)):
            self.cmds = [cmds]
        else:
            self.cmds = cmds
        self.tool_name = tool_name
        self.target = target
        self.out_file = out_file or (
            target if str(target).lower().endswith(".txt") and not os.path.isdir(str(target)) else None
        )
        self.process: subprocess.Popen[Any] | None = None
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label(f"Running {self.tool_name}...", id="task-label")
            total = len(self.cmds) if len(self.cmds) > 1 else None
            yield ProgressBar(total=total, show_eta=False)
            yield Label(f"Target: {escape(self.target)}", id="status-label")

    def on_mount(self) -> None:
        self.progress_bar = self.query_one(ProgressBar)
        self.run_worker(self.run_cmd, exclusive=True, thread=True)

    def action_cancel_process(self):
        self._cancelled = True
        if self.process:
            self._kill_process_group(self.process)
        self.safe_dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_cmd(self):
        worker = get_current_worker()
        bar = self.progress_bar
        is_batch = len(self.cmds) > 1
        failures = []
        captured_output = []

        for idx, cmd in enumerate(self.cmds):
            if self._cancelled or worker.is_cancelled:
                break

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
            except FileNotFoundError:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Command '{cmd[0]}' not found. Is {self.tool_name} installed?",
                    severity="error",
                )
                self.app.call_from_thread(self.safe_dismiss)
                return

            self.app.call_from_thread(
                self.write_log,
                self._log_msg("executing", escape(" ".join(cmd))),
            )

            proc = self.process
            if proc and proc.stdout:
                for line in proc.stdout:
                    self.app.call_from_thread(self.write_log, escape(line.strip()))
                    if self.out_file:
                        captured_output.append(line)
                    if worker.is_cancelled or self._cancelled:
                        self._kill_process_group(proc)
                        break

                proc.wait()
                rc = proc.returncode
                if rc != 0 and rc != -15 and not self._cancelled:
                    failures.append(cmd[-1])
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(cmd[-1])} (exit {rc})"),
                    )
                elif rc == -15:
                    break

            if is_batch and bar:
                self.app.call_from_thread(bar.update, progress=idx + 1)

        if self.out_file and captured_output and not self._cancelled:
            try:
                out_path = os.path.abspath(os.path.expanduser(self.out_file))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.writelines(captured_output)
            except Exception as e:
                self.app.call_from_thread(
                    self.write_log,
                    self._log_msg("failed", f"Failed to save {escape(self.out_file)}: {e}"),
                )

        if self._cancelled or worker.is_cancelled:
            self.app.call_from_thread(
                self.app.notify,
                "Batch Processing Cancelled" if is_batch else "Process Cancelled",
                severity="warning",
            )
        elif is_batch and failures:
            self.app.call_from_thread(
                self.app.notify,
                f"{self.tool_name}: {len(failures)} of {len(self.cmds)} failed (see log).",
                severity="warning",
            )
        elif is_batch:
            self.app.call_from_thread(
                self.app.notify, "Batch Processing Complete!", severity="information"
            )
        elif not failures:
            self.app.call_from_thread(self.app.notify, "Process Complete!", severity="information")

        self.app.call_from_thread(self.safe_dismiss)


class PillowProgressScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(
        self, input_file: str, output_file: str, action: str, dimensions=None, target_ext=None
    ):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.action = action
        self.dimensions = dimensions
        self.target_ext = target_ext
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Processing Image (Pillow)...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Saving: {escape(self.output_file)}", id="status-label")

    def on_mount(self) -> None:
        self.progress_bar = self.query_one(ProgressBar)
        self.run_worker(self.run_pillow, exclusive=True, thread=True)

    def process_image(self, img):
        backend = cast(PillowBackend, get_backend("pillow"))
        return backend.process_image(img, self.action, self.dimensions)

    def run_pillow(self):
        worker = get_current_worker()
        expanded_in = os.path.expanduser(self.input_file)
        expanded_out = os.path.expanduser(self.output_file)

        if self.action == "to_pdf":
            try:
                if os.path.isdir(expanded_in):
                    files = [
                        f
                        for f in os.listdir(expanded_in)
                        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                    ]
                    files = natsorted(files)
                    if not files:
                        self.app.call_from_thread(
                            self.app.notify,
                            f"No images found in {expanded_in}",
                            severity="warning",
                        )
                        self.app.call_from_thread(self.safe_dismiss)
                        return
                    images = []
                    try:
                        for f in files:
                            if self._cancelled or worker.is_cancelled:
                                break
                            with Image.open(os.path.join(expanded_in, f)) as opened_img:
                                images.append(opened_img.convert("RGB"))
                        if not (self._cancelled or worker.is_cancelled) and images:
                            images[0].save(expanded_out, save_all=True, append_images=images[1:])
                            self.app.call_from_thread(self.app.notify, "PDF Created!", severity="information")
                        elif self._cancelled or worker.is_cancelled:
                            self.app.call_from_thread(self.app.notify, "PDF Creation Cancelled", severity="warning")
                    finally:
                        for img in images:
                            try:
                                img.close()
                            except Exception:
                                pass
                else:
                    with Image.open(expanded_in) as img:
                        img.convert("RGB").save(expanded_out)
                self.app.call_from_thread(self.app.notify, "PDF Created!", severity="information")
            except Exception as e:
                self.app.call_from_thread(self.app.notify, f"Error: {escape(str(e))}", severity="error")
            self.app.call_from_thread(self.safe_dismiss)
            return

        if os.path.isdir(expanded_in):
            os.makedirs(expanded_out, exist_ok=True)
            files = [
                f for f in os.listdir(expanded_in) if os.path.isfile(os.path.join(expanded_in, f))
            ]
            files = [
                f
                for f in files
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"))
            ]

            bar = self.progress_bar
            if bar:
                self.app.call_from_thread(bar.update, total=len(files), progress=0)

            failures = []
            for idx, f in enumerate(files):
                if self._cancelled or worker.is_cancelled:
                    break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith("."):
                    ext = "." + ext
                out_f = unique_path(expanded_out, os.path.splitext(f)[0], ext)

                try:
                    with Image.open(in_f) as img:
                        img = self.process_image(img)
                        if out_f.lower().endswith((".jpg", ".jpeg")) and img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        if self.action == "compress":
                            img.save(out_f, optimize=True, quality=int(self.dimensions))
                        else:
                            img.save(out_f)
                except Exception as e:
                    failures.append(f)
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(f)} ({e})"),
                    )
                if bar:
                    self.app.call_from_thread(bar.update, progress=idx + 1)

            if self._cancelled or worker.is_cancelled:
                self.app.call_from_thread(
                    self.app.notify, "Batch Processing Cancelled", severity="warning"
                )
            elif failures:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Batch done. {len(failures)} of {len(files)} failed (see log).",
                    severity="warning",
                )
            else:
                self.app.call_from_thread(
                    self.app.notify, "Batch Processing Complete!", severity="information"
                )
            self.app.call_from_thread(self.safe_dismiss)
            return

        if not os.path.exists(expanded_in):
            self.app.call_from_thread(self.app.notify, "Input image not found.", severity="error")
            self.app.call_from_thread(self.safe_dismiss)
            return

        out_dir = os.path.dirname(expanded_out)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except OSError:
                pass

        try:
            with Image.open(expanded_in) as img:
                img = self.process_image(img)
                if expanded_out.lower().endswith((".jpg", ".jpeg")) and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                if self.action == "compress":
                    img.save(expanded_out, optimize=True, quality=int(self.dimensions))
                else:
                    img.save(expanded_out)
            self.app.call_from_thread(
                self.app.notify, "Image Processing Complete!", severity="information"
            )
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {escape(str(e))}", severity="error")

        self.app.call_from_thread(self.safe_dismiss)

        self.app.call_from_thread(self.safe_dismiss)
