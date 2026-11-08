from workflows.backends.base import Backend
from workflows.backends.chafa import ChafaBackend
from workflows.backends.esrgan import EsrganBackend, RealEsrganBackend
from workflows.backends.gallery_dl import GalleryDlBackend
from workflows.backends.imagemagick import ImageMagickBackend
from workflows.backends.pillow import PillowBackend
from workflows.backends.registry import BackendRegistry
from workflows.backends.whisper import WhisperBackend
from workflows.backends.yt_dlp import YtDlpBackend

backend_registry = BackendRegistry(
    (
        ChafaBackend(),
        EsrganBackend(),
        ImageMagickBackend(),
        PillowBackend(),
        WhisperBackend(),
        YtDlpBackend(),
        GalleryDlBackend(),
    )
)


def get_backend(name: str) -> Backend:
    return backend_registry.get(name)


def register_backend(backend: Backend, *, replace: bool = False) -> Backend:
    return backend_registry.register(backend, replace=replace)


__all__ = [
    "Backend",
    "BackendRegistry",
    "ChafaBackend",
    "EsrganBackend",
    "RealEsrganBackend",
    "GalleryDlBackend",
    "ImageMagickBackend",
    "PillowBackend",
    "WhisperBackend",
    "YtDlpBackend",
    "backend_registry",
    "get_backend",
    "register_backend",
]
