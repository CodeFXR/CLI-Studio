import os
from collections.abc import Sequence

from natsort import natsorted

from workflows.backends.base import Backend
from workflows.utils import IMAGE_EXTENSIONS, file_arg


class ImageMagickBackend(Backend):
    name = "imagemagick"
    operations = frozenset({"filter", "montage", "remove_background"})
    image_extensions = IMAGE_EXTENSIONS

    def __init__(self, executable: str = "magick") -> None:
        self.executable = executable

    def build_command(
        self,
        input_path: str,
        output_path: str,
        arguments: Sequence[str] = (),
    ) -> list[str]:
        return [self.executable, file_arg(input_path), *arguments, file_arg(output_path)]

    def build_cmd(
        self,
        input_path: str,
        output_path: str,
        arguments: Sequence[str] = (),
    ) -> list[str]:
        return self.build_command(input_path, output_path, arguments)

    def build_commands(
        self,
        input_path: str,
        output_path: str,
        arguments: Sequence[str] = (),
    ) -> list[list[str]]:
        expanded_in = os.path.abspath(os.path.expanduser(input_path))
        expanded_out = os.path.abspath(os.path.expanduser(output_path))
        if not os.path.isdir(expanded_in):
            return [self.build_command(expanded_in, expanded_out, arguments)]

        os.makedirs(expanded_out, exist_ok=True)
        files = natsorted(
            filename
            for filename in os.listdir(expanded_in)
            if filename.lower().endswith(self.image_extensions)
            and os.path.isfile(os.path.join(expanded_in, filename))
        )
        return [
            self.build_command(
                os.path.join(expanded_in, filename),
                os.path.join(expanded_out, filename),
                arguments,
            )
            for filename in files
        ]

    def build_cmds(
        self,
        input_path: str,
        output_path: str,
        arguments: Sequence[str] = (),
    ) -> list[list[str]]:
        return self.build_commands(input_path, output_path, arguments)

    def build_montage_command(
        self,
        input_files: Sequence[str],
        tile: str,
        output_path: str,
    ) -> list[str]:
        return [
            self.executable,
            "montage",
            *[file_arg(f) for f in input_files],
            "-tile",
            tile,
            "-geometry",
            "+0+0",
            file_arg(output_path),
        ]
