import atexit
import os
import re
import signal
import subprocess
import tempfile
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
from workflows.utils import open_output_nofollow, unique_path

Image.MAX_IMAGE_PIXELS = 50_000_000

_MAX_IMAGE_PIXELS_LIMIT = 100_000_000
_MAX_PDF_PAGES = 100
_MAX_PDF_TOTAL_PIXELS = 150_000_000

_ACTIVE_PROCESS_GROUPS: set[int] = set()
_PG_LOCK = threading.Lock()

_TERM_GRACE_SECONDS = 1.5

_KILL_LOCKS: dict[int, threading.Lock] = {}
_KILL_LOCKS_GUARD = threading.Lock()


def _kill_lock_for(proc: subprocess.Popen[Any]) -> threading.Lock:
    with _KILL_LOCKS_GUARD:
        return _KILL_LOCKS.setdefault(id(proc), threading.Lock())


def _verified_pgid(proc: subprocess.Popen[Any]) -> int | None:
    pid = getattr(proc, "pid", None)
    if not pid or pid <= 0:
        return None
    if hasattr(os, "getpgid"):
        try:
            pgid = os.getpgid(pid)
        except OSError:
            return None
        return pgid if pgid == pid else None
    return None


def _signal_group_or_process(proc: subprocess.Popen[Any], pgid: int | None, sig: int) -> None:
    try:
        if pgid is not None and hasattr(os, "killpg"):
            os.killpg(pgid, sig)
        elif sig == signal.SIGKILL:
            proc.kill()
        else:
            proc.terminate()
    except (ProcessLookupError, OSError):
        pass


def terminate_process(proc: subprocess.Popen[Any] | None, grace: float = _TERM_GRACE_SECONDS) -> bool:
    if not proc:
        return False
    lock = _kill_lock_for(proc)
    with lock:
        try:
            if proc.poll() is not None:
                _unregister_process_group(getattr(proc, "pid", None))
                return False
            pgid = _verified_pgid(proc)
            _signal_group_or_process(proc, pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                _signal_group_or_process(proc, pgid, signal.SIGKILL)
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=0.5)
                except Exception:
                    pass
            except Exception:
                pass
            _unregister_process_group(getattr(proc, "pid", None))
            return True
        finally:
            with _KILL_LOCKS_GUARD:
                _KILL_LOCKS.pop(id(proc), None)


_kill_process_group = terminate_process


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

    alive = []
    for pgid in active:
        if hasattr(os, "killpg"):
            try:
                os.killpg(pgid, 0)
                alive.append(pgid)
            except (ProcessLookupError, OSError):
                with _PG_LOCK:
                    _ACTIVE_PROCESS_GROUPS.discard(pgid)
        else:
            alive.append(pgid)

    if not alive:
        return

    for pgid in alive:
        try:
            if hasattr(os, "killpg"):
                os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass

    deadline = time.monotonic() + _TERM_GRACE_SECONDS
    remaining = list(alive)
    while remaining and time.monotonic() < deadline:
        still_alive = []
        for pgid in remaining:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(pgid, 0)
                    still_alive.append(pgid)
            except (ProcessLookupError, OSError):
                pass
        remaining = still_alive
        if remaining:
            time.sleep(0.05)

    with _PG_LOCK:
        for pgid in remaining:
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


class _LoggingModalScreen(ModalScreen[Any]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dismissed = False
        self._cancel_event = threading.Event()
        self._kill_dispatched = False
        self._kill_lock = threading.Lock()
        self._app_override = None

    @property
    def _cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @_cancelled.setter
    def _cancelled(self, val: bool) -> None:
        if val:
            self._cancel_event.set()
        else:
            self._cancel_event.clear()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @is_cancelled.setter
    def is_cancelled(self, val: bool) -> None:
        if val:
            self._cancel_event.set()
        else:
            self._cancel_event.clear()

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

    def _request_kill(self, proc: subprocess.Popen[Any] | None) -> None:
        if not proc or proc.poll() is not None:
            return
        threading.Thread(
            target=terminate_process, args=(proc,), daemon=False, name="cli-studio-kill"
        ).start()

    def _dispatch_cancel(self, proc: subprocess.Popen[Any] | None) -> None:
        self._cancel_event.set()
        self._request_kill(proc)
        self.safe_dismiss()

    def _kill_process_group(self, proc: subprocess.Popen[Any] | None, timeout: float = _TERM_GRACE_SECONDS) -> None:
        terminate_process(proc, grace=timeout)

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
        config_warnings: tuple = (),
    ):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.cookies = cookies
        self.remote_components = remote_components
        self.is_audio = is_audio
        self.is_playlist = is_playlist
        self.config_warnings = tuple(config_warnings or ())
        self.process: subprocess.Popen[Any] | None = None
        self.progress_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Downloading Media...", id="task-label")
            yield ProgressBar(total=100, show_eta=True)
            yield Label(f"Saving to: {escape(self.save_path)}", id="status-label")

    def on_mount(self) -> None:
        self.progress_bar = self.query_one(ProgressBar)
        for warning in self.config_warnings:
            self.app.notify(warning, severity="warning")
        self.run_worker(self.run_ytdlp, exclusive=True, thread=True)

    def action_cancel_download(self):
        self._cancelled = True
        self._request_kill(self.process)
        self.safe_dismiss()
        self.app.notify("Download Cancelled", severity="warning")

    def run_ytdlp(self):
        worker = get_current_worker()
        bar = self.progress_bar

        expanded_path = os.path.abspath(os.path.expanduser(self.save_path))
        if os.path.islink(expanded_path):
            self.app.call_from_thread(
                self.app.notify,
                f"Download directory cannot be a symbolic link: {escape(expanded_path)}",
                severity="error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return
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
            if self._cancelled or (worker and worker.is_cancelled):
                proc = self.process
                self._kill_process_group(proc)
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                self.process = None
                self.app.call_from_thread(self.safe_dismiss)
                return
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

                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    terminate_process(proc)
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
        self._request_kill(self.process)
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
                        text=True,
                        start_new_session=True,
                    )
                    _register_process_group(self.process.pid)
                    if self._cancelled or (worker and worker.is_cancelled):
                        proc = self.process
                        self._kill_process_group(proc)
                        if proc.stdout:
                            try:
                                proc.stdout.close()
                            except Exception:
                                pass
                        self.process = None
                        break
                    proc = self.process
                    while True:
                        try:
                            proc.communicate(timeout=0.25)
                            break
                        except subprocess.TimeoutExpired:
                            if self._cancelled or (worker and worker.is_cancelled):
                                self._kill_process_group(proc)
                    rc = self.process.returncode if self.process else 1
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
            if self._cancelled or (worker and worker.is_cancelled):
                proc = self.process
                self._kill_process_group(proc)
                if proc.stdout:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass
                self.process = None
                self.app.call_from_thread(self.safe_dismiss)
                return
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

                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    terminate_process(proc)
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
        self._request_kill(self.process)
        self.safe_dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_cmd(self):
        try:
            worker = get_current_worker()
        except Exception:
            worker = None

        if not self.cmds:
            self.app.call_from_thread(
                self.app.notify,
                "Nothing to run: no commands were built for this selection.",
                severity="warning",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        # Guard both self.target and self.out_file against pre-planted symlinks
        candidates = []
        if self.target:
            candidates.append(self.target)
            if self.tool_name.lower() == "tesseract" and not self.target.lower().endswith(".txt"):
                candidates.append(self.target + ".txt")
        if self.out_file:
            candidates.append(self.out_file)
            if not self.out_file.lower().endswith(".txt"):
                candidates.append(self.out_file + ".txt")

        for target in candidates:
            expanded = os.path.abspath(os.path.expanduser(target))
            if os.path.islink(expanded) or (os.path.lexists(expanded) and not os.path.exists(expanded)):
                self.app.call_from_thread(
                    self.app.notify,
                    f"Target cannot be a symbolic link: {escape(expanded)}",
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
                if self._cancelled or (worker and worker.is_cancelled):
                    proc = self.process
                    self._kill_process_group(proc)
                    if proc.stdout:
                        try:
                            proc.stdout.close()
                        except Exception:
                            pass
                    self.process = None
                    break
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

                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        terminate_process(proc)
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
                if os.path.islink(out_path):
                    self.app.call_from_thread(
                        self.app.notify,
                        f"Output cannot be a symbolic link: {escape(out_path)}",
                        severity="error",
                    )
                else:
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open_output_nofollow(out_path) as f:
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
                out_dir = os.path.dirname(os.path.abspath(expanded_out)) or "."
                os.makedirs(out_dir, exist_ok=True)
                fd, tmp_pdf = tempfile.mkstemp(dir=out_dir, prefix=".cli-studio-pdf-", suffix=".tmp")
                os.close(fd)
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
                        if len(files) > _MAX_PDF_PAGES:
                            raise ValueError(
                                f"Too many images for one PDF: {len(files)} > {_MAX_PDF_PAGES}. "
                                "Split the folder and build one PDF per part."
                            )
                        images = []
                        total_pixels = 0
                        try:
                            for f in files:
                                if self._cancelled or (worker and worker.is_cancelled):
                                    break
                                with Image.open(os.path.join(expanded_in, f)) as opened_img:
                                    pixels = opened_img.width * opened_img.height
                                    if pixels > _MAX_IMAGE_PIXELS_LIMIT:
                                        raise Image.DecompressionBombError(
                                            f"{f}: {pixels:,} pixels exceeds the safety limit"
                                        )
                                    total_pixels += pixels
                                    if total_pixels > _MAX_PDF_TOTAL_PIXELS:
                                        raise Image.DecompressionBombError(
                                            f"Folder exceeds the {_MAX_PDF_TOTAL_PIXELS:,}-pixel "
                                            "total budget for one PDF"
                                        )
                                    images.append(opened_img.convert("RGB"))
                            if not (self._cancelled or (worker and worker.is_cancelled)) and images:
                                images[0].save(tmp_pdf, save_all=True, append_images=images[1:])
                                os.replace(tmp_pdf, expanded_out)
                                tmp_pdf = ""
                                self.app.call_from_thread(
                                    self.app.notify, "PDF Created!", severity="information"
                                )
                            elif self._cancelled or (worker and worker.is_cancelled):
                                self.app.call_from_thread(
                                    self.app.notify, "PDF Creation Cancelled", severity="warning"
                                )
                        finally:
                            for img in images:
                                try:
                                    img.close()
                                except Exception:
                                    pass
                    else:
                        with Image.open(expanded_in) as img:
                            pixels = img.width * img.height
                            if pixels > _MAX_IMAGE_PIXELS_LIMIT:
                                raise Image.DecompressionBombError(
                                    f"{pixels:,} pixels exceeds the safety limit"
                                )
                            img.convert("RGB").save(tmp_pdf)
                        os.replace(tmp_pdf, expanded_out)
                        tmp_pdf = ""
                        self.app.call_from_thread(
                            self.app.notify, "PDF Created!", severity="information"
                        )
                finally:
                    if tmp_pdf:
                        try:
                            os.unlink(tmp_pdf)
                        except OSError:
                            pass
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
                        if img.width * img.height > _MAX_IMAGE_PIXELS_LIMIT:
                            raise Image.DecompressionBombError(
                                f"{f}: {img.width * img.height:,} pixels exceeds the safety limit"
                            )
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

        tmp_target = ""
        try:
            with Image.open(expanded_in) as img:
                if img.width * img.height > _MAX_IMAGE_PIXELS_LIMIT:
                    raise Image.DecompressionBombError(
                        f"{img.width * img.height:,} pixels exceeds the safety limit"
                    )
                img = self.process_image(img)
                if expanded_out.lower().endswith((".jpg", ".jpeg")) and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                out_ext = os.path.splitext(expanded_out)[1]
                tmp_fd, tmp_target = tempfile.mkstemp(
                    dir=out_dir or None, prefix=".cli-studio-img-", suffix=out_ext
                )
                os.close(tmp_fd)

                if self.action == "compress":
                    img.save(tmp_target, optimize=True, quality=int(self.dimensions))
                else:
                    img.save(tmp_target)
            os.replace(tmp_target, expanded_out)
            tmp_target = ""
            self.app.call_from_thread(
                self.app.notify, "Image Processing Complete!", severity="information"
            )
        except Image.DecompressionBombError:
            self.app.call_from_thread(
                self.app.notify, "Error: Image decompression bomb detected", severity="error"
            )
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {escape(str(e))}", severity="error")
        finally:
            if tmp_target:
                try:
                    os.unlink(tmp_target)
                except OSError:
                    pass

        self.app.call_from_thread(self.safe_dismiss)
