import os

from workflows.backends.base import Backend


class GalleryDlBackend(Backend):
    name = "gallery-dl"
    operations = frozenset({"download_gallery"})

    def __init__(self, executable: str = "gallery-dl") -> None:
        self.executable = executable

    def build_command(self, url: str, destination: str) -> list[str]:
        expanded_destination = os.path.abspath(os.path.expanduser(destination))
        return [self.executable, "--dest", expanded_destination, "--", url]

    def build_cmd(self, url: str, destination: str) -> list[str]:
        return self.build_command(url, destination)
