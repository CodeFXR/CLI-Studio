from workflows import (
    audio,
    cloud,
    esrgan,
    handbrake,
    image,
    mkv,
    preview,
    shared,
    transcribe,
    video,
)


def _build_download_video():
    return shared.build_download_flow(is_audio=False)


def _build_download_playlist():
    return shared.build_download_flow(is_audio=False, is_playlist=True)


def _build_download_gallery():
    return shared.build_gallery_dl_flow()


def _build_convert_video():
    return shared.build_convert_media_flow(is_audio=False)


def _build_trim_video():
    return shared.build_trim_media_flow(is_video=True)


def _build_download_audio():
    return shared.build_download_flow(is_audio=True)


def _build_convert_audio():
    return shared.build_convert_media_flow(is_audio=True)


def _build_trim_audio():
    return shared.build_trim_media_flow(is_video=False)


COMMAND_REGISTRY = {
    # Video
    "download video": _build_download_video,
    "download playlist": _build_download_playlist,
    "download gallery": _build_download_gallery,
    "convert video": _build_convert_video,
    "trim video": _build_trim_video,
    "extract audio": video.build_extract_audio_flow,
    "mute video": video.build_mute_video_flow,
    "change video speed": video.build_video_speed_flow,
    "rotate video": video.build_rotate_video_flow,
    "reverse video": video.build_reverse_video_flow,
    "create gif": video.build_create_gif_flow,
    "extract frames": video.build_extract_frames_flow,
    "add watermark": video.build_add_watermark_flow,
    "add audio track": video.build_add_audio_track_flow,
    "scale/resize video": video.build_scale_video_flow,
    "fade in video": video.build_fade_video_flow,
    "extract subtitles": video.build_extract_subs_flow,
    "generate whisper subtitles": transcribe.build_whisper_subtitles_flow,
    "burn subtitles": video.build_burn_subtitles_flow,
    "silence removal": video.build_silence_remove_flow,
    "audio visualizer": video.build_audio_visualizer_flow,
    "convert video preset": video.build_advanced_convert_video_flow,
    "remux video to mkv": mkv.build_remux_to_mkv_flow,
    "merge mkvs": mkv.build_merge_mkvs_flow,
    "extract mkv subs": mkv.build_extract_mkv_subs_flow,
    "add subs to mkv": mkv.build_add_subtitles_to_mkv_flow,
    "extract mkv attachments": mkv.build_extract_mkv_attachments_flow,
    # Audio
    "download audio": _build_download_audio,
    "convert audio": _build_convert_audio,
    "trim audio": _build_trim_audio,
    "change volume": audio.build_change_volume_flow,
    "change audio speed": audio.build_audio_speed_flow,
    "reverse audio": audio.build_reverse_audio_flow,
    "normalize audio": audio.build_normalize_audio_flow,
    "fade in audio": audio.build_fade_audio_flow,
    "mix audio tracks": audio.build_mix_audio_flow,
    "preview audio waveform": preview.build_preview_audio_flow,
    "normalize audio (2-pass)": audio.build_ffmpeg_normalize_flow,
    # Image
    "convert image": image.build_convert_image_flow,
    "resize image": image.build_resize_image_flow,
    "crop image": image.build_crop_image_flow,
    "rotate image": image.build_rotate_image_flow,
    "flip image": image.build_flip_image_flow,
    "remove background color": image.build_remove_bg_color_flow,
    "apply filter": image.build_imagemagick_filter_flow,
    "strip metadata": image.build_exiftool_strip_flow,
    "add text watermark": image.build_text_watermark_flow,
    "optimize/compress": image.build_compress_image_flow,
    "convert to pdf": image.build_images_to_pdf_flow,
    "add border": image.build_add_border_flow,
    "extract text from image": image.build_extract_text_flow,
    "preview image": preview.build_preview_image_flow,
    "upscale image": esrgan.build_upscale_image_flow,
    "sprite sheet": image.build_sprite_sheet_flow,
    "set exif tag": image.build_set_exif_tag_flow,
    "copy exif": image.build_copy_exif_flow,
    "rename by exif date": image.build_rename_by_exif_date_flow,
    "scan barcode": image.build_scan_barcode_flow,
    # Cloud Storage (rclone)
    "rclone copy": cloud.build_rclone_copy_flow,
    "rclone list remotes": cloud.build_rclone_list_remotes_flow,
    # Device Presets (HandBrake)
    "transcode device preset": handbrake.build_handbrake_preset_flow,
    "list handbrake presets": handbrake.build_handbrake_list_presets_flow,
}


class CommandHandler:
    @staticmethod
    def handle_command(command_text: str):
        cmd = command_text.lower()
        if cmd in COMMAND_REGISTRY:
            return COMMAND_REGISTRY[cmd]()
        return f"Selected: {command_text} (No action defined)"
