import os
from typing import Any

from config import validate_cache_dir
from workflows.backends.base import Backend


WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")
WHISPER_DEVICES = ("auto", "cpu", "cuda")
WHISPER_COMPUTE_TYPES = ("auto", "int8", "float16", "float32")


class WhisperBackend(Backend):
    name = "whisper"
    operations = frozenset({"transcribe"})
    models = WHISPER_MODELS
    devices = WHISPER_DEVICES
    compute_types = WHISPER_COMPUTE_TYPES

    def list_models(self) -> list[str]:
        return list(self.models)

    def list_devices(self) -> list[str]:
        return list(self.devices)

    def list_compute_types(self) -> list[str]:
        return list(self.compute_types)

    def default_cache_dir(self) -> str:
        return "~/.cache/cli-studio/whisper"

    def create_model(
        self,
        model_name: str,
        *,
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: str = "",
    ) -> Any:
        from faster_whisper import WhisperModel

        model = model_name if model_name in self.models else "small"
        selected_device = device if device in self.devices else "auto"
        selected_compute = compute_type if compute_type in self.compute_types else "auto"
        selected_cache = validate_cache_dir(cache_dir) or self.default_cache_dir()
        kwargs: dict[str, Any] = {
            "device": selected_device,
            "compute_type": "default" if selected_compute == "auto" else selected_compute,
            "download_root": os.path.abspath(os.path.expanduser(selected_cache)),
        }
        return WhisperModel(model, **kwargs)
