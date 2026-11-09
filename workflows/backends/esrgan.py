from workflows.backends.base import Backend
from workflows.utils import file_arg


class EsrganBackend(Backend):
    name = "esrgan"
    operations = frozenset({"upscale"})
    models = (
        "realesrgan-x4plus",
        "realesrgan-x4plus-anime",
        "realesrgan-x3plus",
        "realesrgan-x2plus",
        "realesr-animevideov3",
    )
    scales = (2, 3, 4)
    available_models = models
    supported_scales = scales

    def __init__(self, executable: str = "realesrgan-ncnn-vulkan") -> None:
        self.executable = executable

    def build_command(
        self,
        input_path: str,
        output_path: str,
        *,
        model: str = "realesrgan-x4plus",
        scale: int = 4,
        tile_size: int = 0,
        gpu_id: int = 0,
    ) -> list[str]:
        selected_model = model if model in self.models else self.models[0]
        selected_scale = scale if scale in self.scales else 4
        command = [
            self.executable,
            "-i",
            file_arg(input_path),
            "-o",
            file_arg(output_path),
            "-n",
            selected_model,
            "-s",
            str(selected_scale),
            "-f",
            "png",
        ]
        if tile_size > 0:
            command.extend(["-t", str(tile_size)])
        if gpu_id > 0:
            command.extend(["-g", str(gpu_id)])
        return command

    def build_cmd(
        self,
        input_path: str,
        output_path: str,
        *,
        model: str = "realesrgan-x4plus",
        scale: int = 4,
        tile_size: int = 0,
        gpu_id: int = 0,
    ) -> list[str]:
        return self.build_command(
            input_path,
            output_path,
            model=model,
            scale=scale,
            tile_size=tile_size,
            gpu_id=gpu_id,
        )


RealEsrganBackend = EsrganBackend
