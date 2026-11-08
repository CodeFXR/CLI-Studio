import os

import config
from ui.screens import FilePickerScreen, OptionSelectScreen
from ui.transcribe import WhisperProgressScreen
from workflows.backends.whisper import WHISPER_COMPUTE_TYPES, WHISPER_DEVICES, WHISPER_MODELS


_LANGUAGE_OPTIONS = ("auto", "en", "es", "fr", "de", "it", "ja", "ko", "zh")
_FORMAT_OPTIONS = ("srt", "vtt")


def build_whisper_subtitles_flow():
    defaults = config._load_full_config()
    configured_model = str(defaults.get("whisper_model", "small"))
    if configured_model not in WHISPER_MODELS:
        configured_model = "small"
    model_options = [
        configured_model,
        *[model for model in WHISPER_MODELS if model != configured_model],
    ]

    def step2(input_file, state):
        state["input_file"] = input_file
        return OptionSelectScreen("Whisper model:", model_options, state, step3)

    def step3(model, state):
        state["model"] = model
        return OptionSelectScreen("Subtitle format:", list(_FORMAT_OPTIONS), state, step4)

    def step4(output_format, state):
        state["output_format"] = output_format
        return OptionSelectScreen("Language:", list(_LANGUAGE_OPTIONS), state, step5)

    def step5(language, state):
        state["language"] = language
        base = os.path.splitext(state["input_file"])[0]
        default_output = f"{base}.{state['output_format']}"
        return FilePickerScreen("Save subtitles as:", default_output, state, step6)

    def step6(output_file, state):
        model = state["model"]
        if model not in WHISPER_MODELS:
            model = str(defaults.get("whisper_model", "small"))
        device = str(defaults.get("whisper_device", "auto"))
        if device not in WHISPER_DEVICES:
            device = "auto"
        compute_type = str(defaults.get("whisper_compute", "auto"))
        if compute_type not in WHISPER_COMPUTE_TYPES:
            compute_type = "auto"
        cache_dir = str(defaults.get("whisper_cache_dir", ""))
        return WhisperProgressScreen(
            state["input_file"],
            output_file,
            model=model,
            language=state["language"],
            device=device,
            compute_type=compute_type,
            cache_dir=cache_dir,
        )

    return FilePickerScreen("Select audio or video file:", "", {}, step2)


build_transcribe_audio_flow = build_whisper_subtitles_flow
build_transcribe_flow = build_whisper_subtitles_flow
