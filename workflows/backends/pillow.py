from typing import Any

from PIL import Image, ImageDraw, ImageOps

from workflows.backends.base import Backend

# Pillow raises DecompressionBombError only above 2x MAX_IMAGE_PIXELS,
# so 50M is what actually errors at ~100 MP (N-1). Set it here, in the
# backend, not only as an import side effect of ui/progress.py, so any
# consumer of the backend gets the cap.
Image.MAX_IMAGE_PIXELS = 50_000_000

MAX_IMAGE_PIXELS_LIMIT = 100_000_000


def check_pixel_budget(width: int, height: int, what: str = "image") -> None:
    if width * height > MAX_IMAGE_PIXELS_LIMIT:
        raise ValueError(
            f"{what} would be {width}x{height} ({width * height:,} pixels), "
            f"above the {MAX_IMAGE_PIXELS_LIMIT:,}-pixel safety limit."
        )


class PillowBackend(Backend):
    name = "pillow"
    operations = frozenset(
        {"border", "compress", "convert", "crop", "flip", "resize", "rotate", "to_pdf", "watermark"}
    )

    def process_image(self, image: Any, operation: str, parameter: Any = None) -> Any:
        check_pixel_budget(image.width, image.height, "source image")
        if operation == "resize" and parameter:
            check_pixel_budget(int(parameter[0]), int(parameter[1]), "resized image")
            image = image.resize(parameter, Image.Resampling.LANCZOS)
        elif operation == "crop" and parameter:
            check_pixel_budget(
                int(parameter[2]) - int(parameter[0]),
                int(parameter[3]) - int(parameter[1]),
                "cropped image",
            )
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
            b = int(parameter)
            check_pixel_budget(image.width + 2 * b, image.height + 2 * b, "bordered image")
            image = ImageOps.expand(image, border=b, fill="black")
        return image
