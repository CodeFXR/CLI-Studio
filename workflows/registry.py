from workflows import shared, video, audio, image

COMMAND_REGISTRY = {
    # Video
    "download video": lambda: shared.build_download_flow(is_audio=False),
    "download playlist": lambda: shared.build_download_flow(is_audio=False, is_playlist=True),
    "convert video": lambda: shared.build_convert_media_flow(is_audio=False),
    "trim video": lambda: shared.build_trim_media_flow(is_video=True),
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
    
    # Audio
    "download audio": lambda: shared.build_download_flow(is_audio=True),
    "convert audio": lambda: shared.build_convert_media_flow(is_audio=True),
    "trim audio": lambda: shared.build_trim_media_flow(is_video=False),
    "change volume": audio.build_change_volume_flow,
    "change audio speed": audio.build_audio_speed_flow,
    "reverse audio": audio.build_reverse_audio_flow,
    "normalize audio": audio.build_normalize_audio_flow,
    "fade in audio": audio.build_fade_audio_flow,
    "mix audio tracks": audio.build_mix_audio_flow,
    
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
}

class CommandHandler:
    @staticmethod
    def handle_command(command_text: str):
        cmd = command_text.lower()
        if cmd in COMMAND_REGISTRY:
            return COMMAND_REGISTRY[cmd]()
        return f"Selected: {command_text} (No action defined)"