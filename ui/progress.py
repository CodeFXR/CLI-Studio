import atexit
import os
import re
import signal
import subprocess
import threading
import time
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

Image.MAX_IMAGE_PIXELS = 100_000_000

_ACTIVE_PROCESS_GROUPS: set[int] = set()
_PG_LOCK = threading.Lock()


def _register_process_group(pgid: int | None) -> None:
    if pgid is not None and pgid > 0:
        with _PG_LOCK:
            _ACTIVE_PROCESS_GROUPS.add(pgid)


def _unregister_process_group(pgid: int | None) -> None:
    if pgid is not None:
        with _PG_LOCK:
            _ACTIVE_PROCESS_GROUPS.discard(pgid)


def cleanup_active_process_groups() -> None:
    """Ensure all spawned background process groups are terminated on app exit."""
    with _PG_LOCK:
        active = list(_ACTIVE_PROCESS_GROUPS)
    if not active:
        return
    for pgid in active:
        try:
            if hasattr(os, "killpg"):
                os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    time.sleep(0.5)
    with _PG_LOCK:
        for pgid in active:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            _ACTIVE_PROCESS_GROUPS.discard(pgid)


atexit.register(cleanup_active_process_groups)


def _ffmpeg_overwrite_flag() -> str:
    overwrite = config.coerce_bool(
        config._load_full_config().get("ffmpeg_overwrite"),
        default=True,
    )
    return "-y" if overwrite else "-n"


def _kill_process_group(proc: subprocess.Popen | None, timeout: float = 1.0) -> None:
    """Terminate an entire process group gracefully (SIGTERM) then forcefully (SIGKILL).

    Monitors the process group as a whole using os.killpg(pgid, 0), ensuring that if the
    leader process exits before its spawned children or grandchildren, escalation to
    SIGKILL is never skipped.
    """
    if not proc:
        return
    pgid = getattr(proc, "pid", None)
    if pgid is None:
        return

    # Phase 1: Graceful SIGTERM
    try:
        if hasattr(os, "killpg"):
            os.killpg(pgid, signal.SIGTERM)
        else:
            proc.terminate()
    except (ProcessLookupError, OSError):
        pass

    # Wait grace period while monitoring the process group
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        proc.poll()
        group_alive = False
        if hasattr(os, "killpg"):
            try:
                os.killpg(pgid, 0)
                group_alive = True
            except (ProcessLookupError, OSError):
                group_alive = False
        elif proc.poll() is None:
            group_alive = True

        if not group_alive:
            _unregister_process_group(pgid)
            return
        time.sleep(0.05)

    # Phase 2: Forceful SIGKILL to eliminate stubborn descendants
    try:
        if hasattr(os, "killpg"):
            os.killpg(pgid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, OSError):
        pass

    try:
        proc.kill()
    except Exception:
        pass

    # Reaping drain loop
    drain_deadline = time.monotonic() + 0.2
    while time.monotonic() < drain_deadline:
        proc.poll()
        if hasattr(os, "killpg"):
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, OSError):
                break
        time.sleep(0.02)

    _unregister_process_group(pgid)


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

    def _kill_process_group(self, proc: subprocess.Popen | None, timeout: float = 1.0) -> None:
        _kill_process_group(proc, timeout=timeout)

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
        proc = self.process
        if proc:
            threading.Thread(target=self._kill_process_group, args=(proc,), daemon=True).start()
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

        if self._cancelled or (worker and worker.is_cancelled):
            self.app.call_from_thread(self.safe_dismiss)
            return

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=True,
            )
            _register_process_group(self.process.pid)
        except FileNotFoundError:
            self.app.call_from_thread(
                self.app.notify, "yt-dlp not found. Please install it.", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Failed to execute yt-dlp: {escape(str(e))}", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        percent_re = re.compile(r"(\d{1,3}\.\d)%")

        proc = self.process
        try:
            if self._cancelled or (worker and worker.is_cancelled):
                self._kill_process_group(proc)
                return

            if proc and proc.stdout:
                for line in proc.stdout:
                    self.app.call_from_thread(self.write_log, escape(line.strip()))
                    if self._cancelled or (worker and worker.is_cancelled):
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
                elif proc.returncode not in (-9, -15) and not (self._cancelled or (worker and worker.is_cancelled)):
                    self.app.call_from_thread(self.app.notify, "Download Failed.", severity="error")
        finally:
            if proc:
                _unregister_process_group(proc.pid)
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
            self.process = None

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
        proc = self.process
        if proc:
            threading.Thread(target=self._kill_process_group, args=(proc,), daemon=True).start()
        self.safe_dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_ffmpeg(self):
        try:
            worker = get_current_worker()
        except Exception:
            worker = None
        expanded_in = os.path.abspath(os.path.expanduser(self.input_file))
        expanded_out = os.path.abspath(os.path.expanduser(self.output_file))
        overwrite_flag = _ffmpeg_overwrite_flag()

        if os.path.islink(expanded_out):
            self.app.call_from_thread(
                self.app.notify,
                f"Output cannot be a symbolic link: {escape(expanded_out)}",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

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
                if self._cancelled or (worker and worker.is_cancelled):
                    break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith("."):
                    ext = "." + ext
                out_f = unique_path(expanded_out, os.path.splitext(f)[0], ext)

                cmd = ["ffmpeg", "-nostdin", overwrite_flag, "-i", in_f] + self.action_args + [out_f]
                try:
                    self.process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )
                    _register_process_group(self.process.pid)
                    if self._cancelled or (worker and worker.is_cancelled):
                        self._kill_process_group(self.process)
                        break
                    _, stderr = self.process.communicate()
                    rc = self.process.returncode
                except Exception:
                    rc = 1
                finally:
                    if self.process:
                        _unregister_process_group(self.process.pid)
                    self.process = None

                if rc != 0 and rc != -15 and not self._cancelled:
                    failures.append(f)
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(f)} (exit {rc})"),
                    )
                if bar:
                    self.app.call_from_thread(bar.update, progress=idx + 1)

            if self._cancelled or (worker and worker.is_cancelled):
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

        if self._cancelled or (worker and worker.is_cancelled):
            self.app.call_from_thread(self.safe_dismiss)
            return

        out_dir = os.path.dirname(expanded_out)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except OSError:
                pass

        cmd = ["ffmpeg", "-nostdin", overwrite_flag, "-i", expanded_in] + self.action_args + [expanded_out]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=True,
            )
            _register_process_group(self.process.pid)
            self.app.call_from_thread(
                self.write_log, self._log_msg("executing", escape(" ".join(cmd)))
            )
        except FileNotFoundError:
            self.app.call_from_thread(
                self.app.notify, "ffmpeg not found. Please install it.", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Failed to execute ffmpeg: {escape(str(e))}", severity="error"
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        proc = self.process
        try:
            if self._cancelled or (worker and worker.is_cancelled):
                self._kill_process_group(proc)
                return

            if proc and proc.stdout:
                for line in proc.stdout:
                    self.app.call_from_thread(self.write_log, escape(line.strip()))
                    if self._cancelled or (worker and worker.is_cancelled):
                        self._kill_process_group(proc)
                        break

                proc.wait()
                if proc.returncode == 0:
                    self.app.call_from_thread(
                        self.app.notify, "Processing Complete!", severity="information"
                    )
                elif proc.returncode not in (-9, -15) and not (self._cancelled or (worker and worker.is_cancelled)):
                    self.app.call_from_thread(self.app.notify, "Processing Failed.", severity="error")
        finally:
            if proc:
                _unregister_process_group(proc.pid)
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
            self.process = None

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
        self.out_file = out_file
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
        proc = self.process
        if proc:
            threading.Thread(target=self._kill_process_group, args=(proc,), daemon=True).start()
        self.safe_dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_cmd(self):
        try:
            worker = get_current_worker()
        except Exception:
            worker = None

        if not self.cmds:
            self.app.call_from_thread(self.safe_dismiss)
            return

        if self.out_file:
            candidates = [self.out_file, self.out_file + ".txt"]
            for target in candidates:
                if os.path.islink(target):
                    self.app.call_from_thread(
                        self.app.notify,
                        f"Output cannot be a symbolic link: {escape(target)}",
                        severity="error",
                    )
                    self.app.call_from_thread(self.safe_dismiss)
                    return

        bar = self.progress_bar
        is_batch = len(self.cmds) > 1
        failures = []
        captured_output = []

        for idx, cmd in enumerate(self.cmds):
            if self._cancelled or (worker and worker.is_cancelled):
                break

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    start_new_session=True,
                )
                _register_process_group(self.process.pid)
            except FileNotFoundError:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Command '{cmd[0]}' not found. Is {self.tool_name} installed?",
                    severity="error",
                )
                self.app.call_from_thread(self.safe_dismiss)
                return
            except Exception as e:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Failed to execute {self.tool_name}: {escape(str(e))}",
                    severity="error",
                )
                self.app.call_from_thread(self.safe_dismiss)
                return

            self.app.call_from_thread(
                self.write_log,
                self._log_msg("executing", escape(" ".join(cmd))),
            )

            proc = self.process
            try:
                if self._cancelled or (worker and worker.is_cancelled):
                    self._kill_process_group(proc)
                    break

                if proc and proc.stdout:
                    for line in proc.stdout:
                        self.app.call_from_thread(self.write_log, escape(line.strip()))
                        if self.out_file:
                            captured_output.append(line)
                        if self._cancelled or (worker and worker.is_cancelled):
                            self._kill_process_group(proc)
                            break

                    proc.wait()
                    rc = proc.returncode
                    if rc != 0 and rc not in (-9, -15) and not self._cancelled:
                        failures.append(cmd[-1])
                        self.app.call_from_thread(
                            self.write_log,
                            self._log_msg("failed", f"{escape(cmd[-1])} (exit {rc})"),
                        )
                    elif rc in (-9, -15):
                        break
            finally:
                if proc:
                    _unregister_process_group(proc.pid)
                    if proc.stdout:
                        try:
                            proc.stdout.close()
                        except Exception:
                            pass
                self.process = None

            if is_batch and bar:
                self.app.call_from_thread(bar.update, progress=idx + 1)

        if self.out_file and captured_output and not self._cancelled:
            try:
                out_path = os.path.abspath(os.path.expanduser(self.out_file))
                if os.path.islink(out_path) or (os.path.lexists(out_path) and not os.path.exists(out_path)):
                    self.app.call_from_thread(
                        self.app.notify,
                        f"Output cannot be a symbolic link: {escape(out_path)}",
                        severity="error",
                    )
                else:
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
                    fd = os.open(out_path, flags, 0o644)
                    with open(fd, "w", encoding="utf-8") as f:
                        f.writelines(captured_output)
            except Exception as e:
                self.app.call_from_thread(
                    self.write_log,
                    self._log_msg("failed", f"Failed to save {escape(self.out_file)}: {e}"),
                )

        if self._cancelled or (worker and worker.is_cancelled):
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
        try:
            worker = get_current_worker()
        except Exception:
            worker = None
        expanded_in = os.path.expanduser(self.input_file)
        expanded_out = os.path.expanduser(self.output_file)

        if self.action == "to_pdf":
            try:
                if os.path.islink(expanded_out):
                    raise ValueError(f"Output path cannot be a symbolic link: {expanded_out}")
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
                            if self._cancelled or (worker and worker.is_cancelled):
                                break
                            with Image.open(os.path.join(expanded_in, f)) as opened_img:
                                images.append(opened_img.convert("RGB"))
                        if not (self._cancelled or (worker and worker.is_cancelled)) and images:
                            images[0].save(expanded_out, save_all=True, append_images=images[1:])
                            self.app.call_from_thread(self.app.notify, "PDF Created!", severity="information")
                        elif self._cancelled or (worker and worker.is_cancelled):
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
            if os.path.islink(expanded_out):
                self.app.call_from_thread(
                    self.app.notify,
                    f"Output directory cannot be a symbolic link: {escape(expanded_out)}",
                    severity="error",
                )
                self.app.call_from_thread(self.safe_dismiss)
                return
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
                if self._cancelled or (worker and worker.is_cancelled):
                    break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith("."):
                    ext = "." + ext
                out_f = unique_path(expanded_out, os.path.splitext(f)[0], ext)
                if os.path.islink(out_f):
                    continue

                try:
                    with Image.open(in_f) as img:
                        img = self.process_image(img)
                        if out_f.lower().endswith((".jpg", ".jpeg")) and img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        if self.action == "compress":
                            img.save(out_f, optimize=True, quality=int(self.dimensions))
                        else:
                            img.save(out_f)
                except Image.DecompressionBombError:
                    failures.append(f)
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(f)} (decompression bomb detected)"),
                    )
                except Exception as e:
                    failures.append(f)
                    self.app.call_from_thread(
                        self.write_log,
                        self._log_msg("failed", f"{escape(f)} ({escape(str(e))})"),
                    )
                if bar:
                    self.app.call_from_thread(bar.update, progress=idx + 1)

            if self._cancelled or (worker and worker.is_cancelled):
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

        if os.path.islink(expanded_out):
            self.app.call_from_thread(
                self.app.notify,
                f"Output cannot be a symbolic link: {escape(expanded_out)}",
                severity="error",
            )
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
        except Image.DecompressionBombError:
            self.app.call_from_thread(
                self.app.notify, "Error: Image decompression bomb detected", severity="error"
            )
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {escape(str(e))}", severity="error")

        self.app.call_from_thread(self.safe_dismiss)
