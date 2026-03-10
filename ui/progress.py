import os
import subprocess
import re
from textual.screen import ModalScreen
from textual.widgets import Label, ProgressBar
from textual.containers import Container
from textual.app import ComposeResult
from textual.worker import get_current_worker

class DownloadProgressScreen(ModalScreen):
    BINDINGS = [("escape", "cancel_download", "Cancel")]

    def __init__(self, url: str, save_path: str, is_audio: bool = False, is_playlist: bool = False):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.is_audio = is_audio
        self.is_playlist = is_playlist
        self.process = None

    def write_log(self, text):
        try:
            log = self.app.query_one("#terminal-log")
            log.write(text)
        except: pass

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Downloading Media...", id="task-label")
            yield ProgressBar(total=100, show_eta=True)
            yield Label(f"Saving to: {self.save_path}", id="status-label")

    def on_mount(self) -> None:
        self.run_worker(self.run_ytdlp, exclusive=True, thread=True)

    def action_cancel_download(self):
        if self.process:
            self.process.terminate()
        self.dismiss()
        self.app.notify("Download Cancelled", severity="warning")

    def run_ytdlp(self):
        worker = get_current_worker()
        bar = self.query_one(ProgressBar)
        
        expanded_path = os.path.abspath(os.path.expanduser(self.save_path))
        if not os.path.exists(expanded_path):
            try: os.makedirs(expanded_path)
            except OSError:
                self.app.call_from_thread(self.app.notify, "Invalid Path", severity="error")
                self.app.call_from_thread(self.dismiss)
                return

        cmd = ["yt-dlp", "--newline"]
        if self.is_audio:
            cmd.extend(["-x", "--audio-format", "mp3"])
        if self.is_playlist:
            cmd.extend(["--yes-playlist"])
        else:
            cmd.extend(["--no-playlist"])
            
        cmd.extend(["-o", f"{expanded_path}/%(title)s.%(ext)s", "--", self.url])

        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except FileNotFoundError:
            self.app.call_from_thread(self.app.notify, "yt-dlp not found. Please install it.", severity="error")
            self.app.call_from_thread(self.dismiss)
            return

        percent_re = re.compile(r'(\d{1,3}\.\d)%')

        for line in self.process.stdout:
            self.app.call_from_thread(self.write_log, line.strip())
            if worker.is_cancelled:
                self.process.terminate()
                break
            
            match = percent_re.search(line)
            if match:
                try:
                    p = float(match.group(1))
                    self.app.call_from_thread(bar.update, progress=p)
                except ValueError: pass

        self.process.wait()
        if self.process.returncode == 0:
            self.app.call_from_thread(self.app.notify, "Download Complete!", severity="information")
        elif self.process.returncode != -15:
            self.app.call_from_thread(self.app.notify, "Download Failed.", severity="error")
            
        self.app.call_from_thread(self.dismiss)


class FfmpegProgressScreen(ModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(self, input_file: str, output_file: str, action_args: list, target_ext: str = None):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.action_args = action_args
        self.target_ext = target_ext
        self.process = None
        
    def write_log(self, text):
        try:
            log = self.app.query_one("#terminal-log")
            log.write(text)
        except: pass

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Processing Media (FFmpeg)...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Output: {self.output_file}", id="status-label")

    def on_mount(self) -> None:
        self.run_worker(self.run_ffmpeg, exclusive=True, thread=True)

    def action_cancel_process(self):
        if self.process:
            self.process.terminate()
        self.dismiss()
        self.app.notify("Process Cancelled", severity="warning")

    def run_ffmpeg(self):
        worker = get_current_worker()
        expanded_in = os.path.abspath(os.path.expanduser(self.input_file))
        expanded_out = os.path.abspath(os.path.expanduser(self.output_file))
        
        # BATCH PROCESSING LOGIC
        if os.path.isdir(expanded_in):
            os.makedirs(expanded_out, exist_ok=True)
            files = [f for f in os.listdir(expanded_in) if os.path.isfile(os.path.join(expanded_in, f))]
            files = [f for f in files if not f.startswith('.')]
            
            bar = self.query_one(ProgressBar)
            self.app.call_from_thread(bar.update, total=len(files), progress=0)
            
            for idx, f in enumerate(files):
                if worker.is_cancelled: break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith('.'): ext = '.' + ext
                out_f = os.path.join(expanded_out, os.path.splitext(f)[0] + ext)
                
                cmd = ["ffmpeg", "-y", "-i", in_f] + self.action_args + [out_f]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.app.call_from_thread(bar.update, progress=idx+1)
                
            self.app.call_from_thread(self.app.notify, "Batch Processing Complete!", severity="information")
            self.app.call_from_thread(self.dismiss)
            return

        # SINGLE FILE LOGIC
        if not os.path.exists(expanded_in):
            self.app.call_from_thread(self.app.notify, "Input file not found.", severity="error")
            self.app.call_from_thread(self.dismiss)
            return

        out_dir = os.path.dirname(expanded_out)
        if out_dir and not os.path.exists(out_dir):
            try: os.makedirs(out_dir)
            except OSError: pass

        cmd = ["ffmpeg", "-y", "-i", expanded_in] + self.action_args + [expanded_out]
        
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.app.call_from_thread(self.write_log, f"[bold #00dadf]Executing:[/bold #00dadf] {' '.join(cmd)}")
        except FileNotFoundError:
            self.app.call_from_thread(self.app.notify, "ffmpeg not found. Please install it.", severity="error")
            self.app.call_from_thread(self.dismiss)
            return

        for line in self.process.stdout:
            self.app.call_from_thread(self.write_log, line.strip())
            if worker.is_cancelled:
                self.process.terminate()
                break

        self.process.wait()
        if self.process.returncode == 0:
            self.app.call_from_thread(self.app.notify, "Processing Complete!", severity="information")
        elif self.process.returncode != -15:
            self.app.call_from_thread(self.app.notify, "Processing Failed.", severity="error")
            
        self.app.call_from_thread(self.dismiss)


class GenericCliProgressScreen(ModalScreen):
    BINDINGS = [("escape", "cancel_process", "Cancel")]

    def __init__(self, cmd: list, tool_name: str, target: str):
        super().__init__()
        self.cmd = cmd
        self.tool_name = tool_name
        self.target = target
        self.process = None

    def write_log(self, text):
        try:
            log = self.app.query_one("#terminal-log")
            log.write(text)
        except: pass

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label(f"Running CLI Process...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Target: {self.target}", id="status-label")

    def on_mount(self) -> None:
        self.run_worker(self.run_cmd, exclusive=True, thread=True)

    def action_cancel_process(self):
        if self.process:
            self.process.terminate()
        self.dismiss()
        self.app.notify(f"Process Cancelled", severity="warning")

    def run_cmd(self):
        worker = get_current_worker()
        try:
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.app.call_from_thread(self.write_log, f"[bold #00dadf]Executing:[/bold #00dadf] {' '.join(self.cmd)}")
        except FileNotFoundError:
            self.app.call_from_thread(self.app.notify, f"Command '{self.cmd[0]}' not found. Is {self.tool_name} installed?", severity="error")
            self.app.call_from_thread(self.dismiss)
            return

        for line in self.process.stdout:
            self.app.call_from_thread(self.write_log, line.strip())
            if worker.is_cancelled:
                self.process.terminate()
                break

        self.process.wait()
        if self.process.returncode == 0:
            self.app.call_from_thread(self.app.notify, f"Process Complete!", severity="information")
        elif self.process.returncode != -15:
            self.app.call_from_thread(self.app.notify, f"Process Failed.", severity="error")
            
        self.app.call_from_thread(self.dismiss)


class PillowProgressScreen(ModalScreen):
    def __init__(self, input_file: str, output_file: str, action: str, dimensions=None, target_ext=None):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.action = action
        self.dimensions = dimensions
        self.target_ext = target_ext
        
    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Label("Processing Image (Pillow)...", id="task-label")
            yield ProgressBar(total=None, show_eta=False)
            yield Label(f"Saving: {self.output_file}", id="status-label")

    def on_mount(self) -> None:
        self.run_worker(self.run_pillow, exclusive=True, thread=True)

    def process_image(self, img):
        from PIL import Image, ImageOps, ImageDraw
        if self.action == "resize" and self.dimensions:
            img = img.resize(self.dimensions, Image.Resampling.LANCZOS)
        elif self.action == "crop" and self.dimensions:
            img = img.crop(self.dimensions)
        elif self.action == "rotate" and self.dimensions is not None:
            img = img.rotate(-self.dimensions, expand=True)
        elif self.action == "flip" and self.dimensions:
            if self.dimensions == 'horizontal': img = ImageOps.mirror(img)
            elif self.dimensions == 'vertical': img = ImageOps.flip(img)
        elif self.action == "watermark" and self.dimensions:
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), str(self.dimensions), fill="white")
        elif self.action == "border" and self.dimensions:
            img = ImageOps.expand(img, border=int(self.dimensions), fill='black')
        return img

    def run_pillow(self):
        worker = get_current_worker()
        expanded_in = os.path.expanduser(self.input_file)
        expanded_out = os.path.expanduser(self.output_file)
        
        from PIL import Image
        
        # PDF EXPORT LOGIC
        if self.action == "to_pdf":
            try:
                if os.path.isdir(expanded_in):
                    files = sorted([f for f in os.listdir(expanded_in) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
                    if not files: return
                    images = []
                    for f in files:
                        img = Image.open(os.path.join(expanded_in, f)).convert("RGB")
                        images.append(img)
                    images[0].save(expanded_out, save_all=True, append_images=images[1:])
                else:
                    with Image.open(expanded_in) as img:
                        img.convert("RGB").save(expanded_out)
                self.app.call_from_thread(self.app.notify, "PDF Created!", severity="information")
            except Exception as e:
                self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
            self.app.call_from_thread(self.dismiss)
            return

        # BATCH LOGIC
        if os.path.isdir(expanded_in):
            os.makedirs(expanded_out, exist_ok=True)
            files = [f for f in os.listdir(expanded_in) if os.path.isfile(os.path.join(expanded_in, f))]
            files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'))]
            
            bar = self.query_one(ProgressBar)
            self.app.call_from_thread(bar.update, total=len(files), progress=0)
            
            for idx, f in enumerate(files):
                if worker.is_cancelled: break
                in_f = os.path.join(expanded_in, f)
                ext = self.target_ext if self.target_ext else os.path.splitext(f)[1]
                if not ext.startswith('.'): ext = '.' + ext
                out_f = os.path.join(expanded_out, os.path.splitext(f)[0] + ext)
                
                try:
                    with Image.open(in_f) as img:
                        img = self.process_image(img)
                        if out_f.lower().endswith(('.jpg', '.jpeg')) and img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        if self.action == "compress":
                            img.save(out_f, optimize=True, quality=int(self.dimensions))
                        else:
                            img.save(out_f)
                except Exception: pass
                self.app.call_from_thread(bar.update, progress=idx+1)
                
            self.app.call_from_thread(self.app.notify, "Batch Processing Complete!", severity="information")
            self.app.call_from_thread(self.dismiss)
            return

        # SINGLE FILE LOGIC
        if not os.path.exists(expanded_in):
            self.app.call_from_thread(self.app.notify, "Input image not found.", severity="error")
            self.app.call_from_thread(self.dismiss)
            return
        
        out_dir = os.path.dirname(expanded_out)
        if out_dir and not os.path.exists(out_dir):
            try: os.makedirs(out_dir)
            except OSError: pass

        try:
            with Image.open(expanded_in) as img:
                img = self.process_image(img)
                if expanded_out.lower().endswith(('.jpg', '.jpeg')) and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                if self.action == "compress":
                    img.save(expanded_out, optimize=True, quality=int(self.dimensions))
                else:
                    img.save(expanded_out)
            self.app.call_from_thread(self.app.notify, "Image Processing Complete!", severity="information")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")

        self.app.call_from_thread(self.dismiss)