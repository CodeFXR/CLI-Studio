import os

from workflows.backends.base import Backend


class YtDlpBackend(Backend):
    name = "yt-dlp"
    operations = frozenset({"download_audio", "download_playlist", "download_video"})

    def __init__(self, executable: str = "yt-dlp") -> None:
        self.executable = executable

    def build_command(
        self,
        url: str,
        save_path: str,
        *,
        cookies: str = "",
        remote_components: str = "",
        is_audio: bool = False,
        is_playlist: bool = False,
    ) -> list[str]:
        expanded_path = os.path.abspath(os.path.expanduser(save_path))
        command = [self.executable, "--newline", "--js-runtimes", "node"]
        if cookies:
            command.extend(["--cookies-from-browser", cookies])
        if remote_components:
            command.extend(["--remote-components", remote_components])
        if is_audio:
            command.extend(["-x", "--audio-format", "mp3"])
        command.append("--yes-playlist" if is_playlist else "--no-playlist")
        command.extend(["-o", f"{expanded_path}/%(title)s.%(ext)s", "--", url])
        return command

    def build_cmd(
        self,
        url: str,
        save_path: str,
        *,
        cookies: str = "",
        remote_components: str = "",
        is_audio: bool = False,
        is_playlist: bool = False,
    ) -> list[str]:
        return self.build_command(
            url,
            save_path,
            cookies=cookies,
            remote_components=remote_components,
            is_audio=is_audio,
            is_playlist=is_playlist,
        )
