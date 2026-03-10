MENU_MAIN = ["Video Tools", "Audio Tools", "Image Tools"] 
MENU_VIDEO = [
    "Download Video", "Download Playlist", "Convert Video", 
    "Trim Video", "Extract Audio", "Mute Video", 
    "Change Video Speed", "Rotate Video", "Reverse Video",
    "Create GIF", "Extract Frames",
    "Add Watermark", "Add Audio Track", "Scale/Resize Video", 
    "Fade In Video", "Extract Subtitles"
]
MENU_AUDIO = [
    "Download Audio", "Convert Audio", "Trim Audio", 
    "Change Volume", "Change Audio Speed", "Reverse Audio",
    "Normalize Audio", "Fade In Audio", "Mix Audio Tracks"
]
MENU_IMAGE = [
    "Convert Image", "Resize Image", "Crop Image", 
    "Rotate Image", "Flip Image", "Remove Background Color",
    "Apply Filter", "Strip Metadata",
    "Add Text Watermark", "Optimize/Compress", "Convert to PDF", "Add Border"
]

MENUS = {
    "main": MENU_MAIN,
    "video": MENU_VIDEO,
    "audio": MENU_AUDIO,
    "image": MENU_IMAGE,
}

HELP_REGISTRY = {
    "download video": "Downloads a video from a URL (YouTube, Vimeo, etc.) to your local machine.",
    "download playlist": "Downloads all videos in a specified YouTube/Vimeo playlist.",
    "extract audio": "Strips the video stream and saves only the audio track as an MP3.",
    "trim video": "Cuts a segment of the video. Enter start and end times in seconds or HH:MM:SS format.\nExample: Start 00:01:00, End 00:02:00 extracts 1 minute.",
    "trim audio": "Cuts a segment of the audio track. Uses precise timestamps to extract exactly what you need without re-encoding.",
    "change video speed": "Speeds up or slows down the video while maintaining audio sync.",
    "convert image": "Changes the file format of an image (e.g., from PNG to JPG). Automatically handles transparency.",
    "resize image": "Changes the dimensions of an image using high-quality Lanczos resampling.\nEnter resolution as WidthxHeight (e.g., 1920x1080).",
    "remove background color": "Deletes a solid background color from an image, making it transparent. Uses ImageMagick's fuzz factor to handle slight gradients.",
    "apply filter": "Applies a predefined aesthetic filter to your image using ImageMagick.",
    "strip metadata": "Removes all EXIF, GPS, and tracking data from an image or video for privacy.",
    "add watermark": "Overlays a second image (like a PNG logo) onto a video in the bottom right corner.",
    "normalize audio": "Levels out audio so quiet parts are louder and loud parts are softer. Great for podcasts.",
    "convert to pdf": "Combines a folder of images into a single, multi-page PDF document.",
}
def get_help(cmd):
    return HELP_REGISTRY.get(cmd, f"Runs the '{cmd}' tool. Follow the on-screen prompts to configure your inputs and execute.")
