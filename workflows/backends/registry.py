from collections.abc import Iterable

from workflows.backends.base import Backend


_BACKEND_ALIASES = {
    "image_magick": "imagemagick",
    "magick": "imagemagick",
    "yt_dlp": "yt-dlp",
    "ytdlp": "yt-dlp",
    "gallery_dl": "gallery-dl",
    "gallerydl": "gallery-dl",
}


class BackendRegistry:
    def __init__(self, backends: Iterable[Backend] = ()) -> None:
        self._backends: dict[str, Backend] = {}
        for backend in backends:
            self.register(backend)

    def register(self, backend: Backend, *, replace: bool = False) -> Backend:
        if not isinstance(backend, Backend):
            raise TypeError("Backends must inherit from Backend")
        name = backend.name.strip().lower()
        if not name:
            raise ValueError("Backend name cannot be empty")
        if name in self._backends and not replace:
            raise ValueError(f"Backend already registered: {name}")
        self._backends[name] = backend
        return backend

    def get(self, name: str) -> Backend:
        normalized = name.strip().lower()
        normalized = _BACKEND_ALIASES.get(normalized, normalized)
        try:
            return self._backends[normalized]
        except KeyError as error:
            available = ", ".join(self.names())
            raise KeyError(f"Unknown backend '{name}'. Available: {available}") from error

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))

    def __contains__(self, name: object) -> bool:
        if not isinstance(name, str):
            return False
        normalized = _BACKEND_ALIASES.get(name.strip().lower(), name.strip().lower())
        return normalized in self._backends
