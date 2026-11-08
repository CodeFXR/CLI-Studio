from typing import Any

from PIL import Image, ImageDraw, ImageOps

from workflows.backends.base import Backend


class PillowBackend(Backend):
    name = "pillow"
    operations = frozenset(
        {"border", "compress", "convert", "crop", "flip", "resize", "rotate", "to_pdf", "watermark"}
    )

    def process_image(self, image: Any, operation: str, parameter: Any = None) -> Any:
        if operation == "resize" and parameter:
            image = image.resize(parameter, Image.Resampling.LANCZOS)
        elif operation == "crop" and parameter:
            image = image.crop(parameter)
        elif operation == "rotate" and parameter is not None:
            image = image.rotate(-parameter, expand=True)
        elif operation == "flip" and parameter:
            if parameter == "horizontal":
                image = ImageOps.mirror(image)
            elif parameter == "vertical":
                image = ImageOps.flip(image)
        elif operation == "watermark" and parameter:
            draw = ImageDraw.Draw(image)
            draw.text((20, 20), str(parameter), fill="white")
        elif operation == "border" and parameter:
            image = ImageOps.expand(image, border=int(parameter), fill="black")
        return image
