import os

# 1. Update config.py
with open('/home/jvm/projects/cli-studio/config.py', 'a') as f:
    f.write('''\n
HELP_REGISTRY = {
    "download video": "Downloads a video from a URL (YouTube, Vimeo, etc.) to your local machine.",
    "download playlist": "Downloads all videos in a specified YouTube/Vimeo playlist.",
    "extract audio": "Strips the video stream and saves only the audio track as an MP3.",
    "trim video": "Cuts a segment of the video. Enter start and end times in seconds or HH:MM:SS format.\\nExample: Start 00:01:00, End 00:02:00 extracts 1 minute.",
    "trim audio": "Cuts a segment of the audio track. Uses precise timestamps to extract exactly what you need without re-encoding.",
    "change video speed": "Speeds up or slows down the video while maintaining audio sync.",
    "convert image": "Changes the file format of an image (e.g., from PNG to JPG). Automatically handles transparency.",
    "resize image": "Changes the dimensions of an image using high-quality Lanczos resampling.\\nEnter resolution as WidthxHeight (e.g., 1920x1080).",
    "remove background color": "Deletes a solid background color from an image, making it transparent. Uses ImageMagick's fuzz factor to handle slight gradients.",
    "apply filter": "Applies a predefined aesthetic filter to your image using ImageMagick.",
    "strip metadata": "Removes all EXIF, GPS, and tracking data from an image or video for privacy.",
    "add watermark": "Overlays a second image (like a PNG logo) onto a video in the bottom right corner.",
    "normalize audio": "Levels out audio so quiet parts are louder and loud parts are softer. Great for podcasts.",
    "convert to pdf": "Combines a folder of images into a single, multi-page PDF document.",
}
def get_help(cmd):
    return HELP_REGISTRY.get(cmd, f"Runs the '{cmd}' tool. Follow the on-screen prompts to configure your inputs and execute.")
''')

# 2. Create workflows/utils.py
with open('/home/jvm/projects/cli-studio/workflows/utils.py', 'w') as f:
    f.write('''import subprocess
import os

def get_media_duration(filepath):
    try:
        expanded = os.path.expanduser(filepath)
        if not os.path.isfile(expanded): return "00:01:00"
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", expanded]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1)
        duration = float(res.stdout.strip())
        h = int(duration // 3600)
        m = int((duration % 3600) // 60)
        s = int(duration % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "00:01:00"
''')

# 3. Patch workflows/shared.py to use ffprobe
with open('/home/jvm/projects/cli-studio/workflows/shared.py', 'r') as f:
    content = f.read()

content = content.replace("from ui.progress import", "from workflows.utils import get_media_duration\nfrom ui.progress import")
content = content.replace('return TextInputScreen("End Time:", "e.g. 00:02:45 or 165", "00:01:00", state, step4)', 
                          'end_time = get_media_duration(state["in_file"])\n        return TextInputScreen("End Time:", "e.g. 00:02:45 or 165", end_time, state, step4)')

with open('/home/jvm/projects/cli-studio/workflows/shared.py', 'w') as f:
    f.write(content)

# 4. Patch studio_themes.py for Log and Help styles
with open('/home/jvm/projects/cli-studio/studio_themes.py', 'r') as f:
    content = f.read()

content = content.replace('Screen.menu-open #menu-panel { display: block; }', 
'''Screen.menu-open #menu-panel { display: block; }
Screen.log-open #help-text { display: none; }
Screen.log-open #terminal-log { display: block; }

#terminal-log {
    width: 100%;
    height: 100%;
    display: none;
    border: tall #888888;
    background: transparent;
    padding: 0 1;
}
#help-body {
    width: 100%;
    margin: 1 0;
    content-align: center middle;
    color: #cccccc;
}
''')
with open('/home/jvm/projects/cli-studio/studio_themes.py', 'w') as f:
    f.write(content)

# 5. Patch ui/progress.py to log to terminal-log
with open('/home/jvm/projects/cli-studio/ui/progress.py', 'r') as f:
    content = f.read()
    
log_func = '''
    def write_log(self, text):
        try:
            log = self.app.query_one("#terminal-log")
            log.write(text)
        except: pass
'''
content = content.replace('class DownloadProgressScreen', log_func + '\\nclass DownloadProgressScreen')
content = content.replace('for line in self.process.stdout:\\n            if worker', 
                          'for line in self.process.stdout:\\n            self.app.call_from_thread(self.write_log, line.strip())\\n            if worker')
                          
with open('/home/jvm/projects/cli-studio/ui/progress.py', 'w') as f:
    f.write(content)

print("Patch script executed successfully.")
