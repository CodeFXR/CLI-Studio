import os
from typing import cast

from natsort import natsorted

from ui.progress import GenericCliProgressScreen
from ui.screens import FilePickerScreen, OptionSelectScreen
from workflows.backends import EsrganBackend, get_backend


_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
_TILE_OPTIONS = ("auto", "256", "512")


def build_upscale_image_flow():
    backend = cast(EsrganBackend, get_backend("esrgan"))

    def step2(input_path, state):
        state["input_path"] = input_path
        return OptionSelectScreen("Upscaler model:", list(backend.models), state, step3)

    def step3(model, state):
        state["model"] = model
        return OptionSelectScreen("Scale:", [f"{scale}x" for scale in backend.scales], state, step4)

    def step4(scale, state):
        state["scale"] = int(scale.rstrip("x"))
        return OptionSelectScreen("Tile size:", list(_TILE_OPTIONS), state, step5)

    def step5(tile, state):
        state["tile_size"] = 0 if tile == "auto" else int(tile)
        input_path = os.path.abspath(os.path.expanduser(state["input_path"]))
        if os.path.isdir(input_path):
            default_output = os.path.join(input_path, "upscaled")
        else:
            base = os.path.splitext(input_path)[0]
            default_output = f"{base}_upscaled_x{state['scale']}.png"
        return FilePickerScreen("Save upscaled image(s) as:", default_output, state, step6)

    def step6(output_path, state):
        input_path = os.path.abspath(os.path.expanduser(state["input_path"]))
        output_path = os.path.abspath(os.path.expanduser(output_path))
        model = state["model"]
        scale = state["scale"]
        tile_size = state["tile_size"]
        if os.path.isdir(input_path):
            os.makedirs(output_path, exist_ok=True)
            files = natsorted(
                filename
                for filename in os.listdir(input_path)
                if filename.lower().endswith(_IMAGE_EXTENSIONS)
                and os.path.isfile(os.path.join(input_path, filename))
            )
            commands = [
                backend.build_command(
                    os.path.join(input_path, filename),
                    os.path.join(output_path, f"{os.path.splitext(filename)[0]}_x{scale}.png"),
                    model=model,
                    scale=scale,
                    tile_size=tile_size,
                )
                for filename in files
            ]
            if not commands:
                return None
            return GenericCliProgressScreen(commands, "Real-ESRGAN", output_path)

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        command = backend.build_command(
            input_path,
            output_path,
            model=model,
            scale=scale,
            tile_size=tile_size,
        )
        return GenericCliProgressScreen(command, "Real-ESRGAN", output_path)

    return FilePickerScreen("Select image file or folder:", "", {}, step2)
