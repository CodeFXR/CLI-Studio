import os
import tempfile
from typing import Literal, cast

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, ProgressBar
from textual.worker import get_current_worker

from ui.progress import _LoggingModalScreen
from workflows.backends import WhisperBackend, get_backend


def _format_subtitle_timestamp(seconds: float, *, vtt: bool = False) -> str:
    milliseconds_total = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    separator = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{milliseconds:03d}"


class WhisperProgressScreen(_LoggingModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(
        self,
        input_file: str,
        output_file: str,
        model: str = "small",
        language: str = "auto",
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: str = "",
    ) -> None:
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.model = model
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.cache_dir = cache_dir
        self.progress_bar: ProgressBar | None = None
        self.status_label: Label | None = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Generating Whisper Subtitles...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Model: {self.model}  Output: {escape(self.output_file)}", id="status-label")

    def on_mount(self) -> None:
        try:
            self.progress_bar = self.query_one(ProgressBar)
            self.status_label = self.query_one("#status-label", Label)
        except Exception:
            pass
        self.run_worker(self.run_whisper, exclusive=True, thread=True)

    def action_cancel_process(self) -> None:
        if self._cancelled:
            # Second Esc: the user insists on closing the screen. The
            # worker may still be blocked inside native faster-whisper
            # code; it owns its temp file and will discard the result.
            self.safe_dismiss()
            return
        self._cancelled = True
        self._set_status(
            "Cancelling... stops after the current step (model load / segment). "
            "Esc again to close this screen only."
        )
        self.app.notify(
            "Cancellation requested - transcription will stop at the next checkpoint.",
            severity="warning",
        )

    def _set_status(self, message: str) -> None:
        if self.status_label:
            try:
                self.status_label.update(message)
            except Exception:
                pass

    def _set_progress(self, *, total: float | None = None, progress: float = 0) -> None:
        if self.progress_bar:
            try:
                self.progress_bar.update(total=total, progress=progress)
            except Exception:
                pass

    def _notify(
        self,
        message: str,
        severity: Literal["information", "warning", "error"] = "information",
    ) -> None:
        self.app.notify(message, severity=severity)

    def _write_segment(
        self, handle, index: int, start: float, end: float, text: str, vtt: bool
    ) -> None:
        if vtt:
            handle.write(
                f"{_format_subtitle_timestamp(start, vtt=True)} --> "
                f"{_format_subtitle_timestamp(end, vtt=True)}\n{text}\n\n"
            )
        else:
            handle.write(f"{index}\n")
            handle.write(
                f"{_format_subtitle_timestamp(start)} --> {_format_subtitle_timestamp(end)}\n"
            )
            handle.write(f"{text}\n\n")

    def run_whisper(self) -> None:
        try:
            worker = get_current_worker()
        except Exception:
            worker = None
        expanded_in = os.path.abspath(os.path.expanduser(self.input_file))
        expanded_out = os.path.abspath(os.path.expanduser(self.output_file))
        temp_path = ""

        if os.path.islink(expanded_out):
            self.app.call_from_thread(
                self._notify,
                f"Output cannot be a symbolic link: {escape(expanded_out)}",
                "error",
            )
            self.app.call_from_thread(self.safe_dismiss)
            return

        if self._cancelled or (worker and worker.is_cancelled):
            self.app.call_from_thread(self.safe_dismiss)
            return

        try:
            if not os.path.exists(expanded_in):
                raise FileNotFoundError(expanded_in)
            out_dir = os.path.dirname(expanded_out)
            os.makedirs(out_dir, exist_ok=True)
            backend = cast(WhisperBackend, get_backend("whisper"))
            self.app.call_from_thread(self._set_status, f"Loading Whisper model: {self.model}")
            model = backend.create_model(
                self.model,
                device=self.device,
                compute_type=self.compute_type,
                cache_dir=self.cache_dir,
            )
            if self._cancelled or (worker and worker.is_cancelled):
                self.app.call_from_thread(self._notify, "Transcription cancelled", "warning")
                self.app.call_from_thread(self.safe_dismiss)
                return
            language = None if self.language in ("", "auto") else self.language
            segments, info = model.transcribe(
                expanded_in,
                language=language,
                beam_size=5,
                vad_filter=True,
            )
            duration = float(getattr(info, "duration", 0) or 0)
            if duration > 0:
                self.app.call_from_thread(
                    self._set_progress,
                    total=duration,
                    progress=0,
                )
            fd, temp_path = tempfile.mkstemp(
                dir=out_dir,
                prefix=".cli_studio_subtitles.",
                suffix=".tmp",
            )
            vtt = expanded_out.lower().endswith(".vtt")
            count = 0
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                if vtt:
                    handle.write("WEBVTT\n\n")
                for segment in segments:
                    if self._cancelled or (worker and worker.is_cancelled):
                        break
                    text = str(getattr(segment, "text", "")).strip()
                    if not text:
                        continue
                    count += 1
                    start = float(getattr(segment, "start", 0))
                    end = float(getattr(segment, "end", start))
                    self._write_segment(handle, count, start, end, text, vtt)
                    self.app.call_from_thread(
                        self.write_log,
                        escape(f"[{start:.2f} -> {end:.2f}] {text}"),
                    )
                    if duration > 0:
                        self.app.call_from_thread(
                            self._set_progress,
                            total=duration,
                            progress=min(end, duration),
                        )

            if self._cancelled or (worker and worker.is_cancelled):
                os.unlink(temp_path)
                temp_path = ""
                self.app.call_from_thread(self._notify, "Transcription cancelled", "warning")
            else:
                if os.path.islink(expanded_out):
                    os.unlink(temp_path)
                    temp_path = ""
                    self.app.call_from_thread(
                        self._notify,
                        f"Output cannot be a symbolic link: {escape(expanded_out)}",
                        "error",
                    )
                else:
                    os.replace(temp_path, expanded_out)
                    temp_path = ""
                    self.app.call_from_thread(
                        self._notify,
                        f"Generated {count} subtitle segments.",
                        "information",
                    )
        except ImportError:
            self.app.call_from_thread(
                self._notify,
                "faster-whisper is not installed. Run pip install 'faster-whisper>=1.0' first.",
                "error",
            )
        except FileNotFoundError:
            self.app.call_from_thread(self._notify, "Transcription input was not found.", "error")
        except Exception as error:
            self.app.call_from_thread(self._notify, f"Whisper failed: {escape(str(error))}", "error")
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            self.app.call_from_thread(self.safe_dismiss)
