import subprocess
import os

def get_media_duration(filepath):
    try:
        expanded = os.path.abspath(os.path.expanduser(filepath))
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
