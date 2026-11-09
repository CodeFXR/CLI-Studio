import config
from workflows.backends.base import Backend


class ChafaBackend(Backend):
    name = "chafa"
    operations = frozenset({"preview_image", "preview_waveform"})
    formats = ("symbols", "sixels", "kitty", "iterm")

    def __init__(self, executable: str = "chafa") -> None:
        self.executable = executable

    @staticmethod
    def _ffmpeg_overwrite_flag() -> str:
        overwrite = config.coerce_bool(
            config._load_full_config().get("ffmpeg_overwrite"),
            default=True,
        )
        return "-y" if overwrite else "-n"

    def build_render_command(
        self,
        input_path: str,
        *,
        width: int = 80,
        height: int = 24,
        output_format: str = "symbols",
    ) -> list[str]:
        if output_format not in self.formats:
            raise ValueError(f"Unsupported chafa format: {output_format}")
        return [
            self.executable,
            "--size",
            f"{width}x{height}",
            "--format",
            output_format,
            input_path,
        ]

    def build_cmd(
        self,
        input_path: str,
        *,
        width: int = 80,
        height: int = 24,
        output_format: str = "symbols",
    ) -> list[str]:
        return self.build_render_command(
            input_path,
            width=width,
            height=height,
            output_format=output_format,
        )

    def build_waveform_command(
        self,
        input_path: str,
        output_path: str,
        *,
        width: int = 1920,
        height: int = 240,
    ) -> list[str]:
        return [
            "ffmpeg",
            self._ffmpeg_overwrite_flag(),
            "-nostdin",
            "-i",
            input_path,
            "-filter_complex",
            f"showwaves=s={width}x{height}:mode=cline:colors=white",
            "-frames:v",
            "1",
            output_path,
        ]

    def build_audiowaveform_command(
        self,
        input_path: str,
        output_path: str,
        *,
        pixels_per_second: int = 60,
    ) -> list[str]:
        return [
            "audiowaveform",
            "-i",
            input_path,
            "-o",
            output_path,
            "--pixels-per-second",
            str(pixels_per_second),
            "--zoom",
            "1",
        ]
