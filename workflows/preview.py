from ui.preview import PreviewModalScreen
from ui.screens import FilePickerScreen


def build_preview_image_flow():
    def step2(input_path, state):
        return PreviewModalScreen(input_path, "image")

    return FilePickerScreen("Select Image File:", "", {}, step2)


def build_preview_audio_flow():
    def step2(input_path, state):
        return PreviewModalScreen(input_path, "audio")

    return FilePickerScreen("Select Audio File:", "", {}, step2)
