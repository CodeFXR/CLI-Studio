# CLI-Studio — Security Notes

> **Purpose.** What cli-studio does and does not promise about security, for users who want to know what their TUI is doing under the hood.

---

## Threat model

CLI-Studio is a **single-user desktop application** that wraps external CLI tools (`ffmpeg`, `yt-dlp`, `exiftool`, `rclone`, etc.). The user is the operator; the user runs commands on their own files. The threat model is:

- **Adversary**: a malicious file the user has been tricked into processing, or a typo in a path.
- **Not in scope**: web-server threats, cross-user attacks, sandbox escapes between users, network exfiltration.

The security posture is "do not introduce new escalation paths beyond what the wrapped CLI tools already provide." We do not promise that running cli-studio is safer than running `ffmpeg` directly.

---

## What cli-studio does to keep you safe

### Subprocess invocation

Every external command is invoked via `subprocess.Popen(cmd, ...)` or `subprocess.run(cmd, ...)` with **list-form args**, never `shell=True`. There is no shell-interpolation vector — every argv element is a literal string. (`grep -rn "shell=True" workflows/ ui/ cli_studio.py config.py studio_themes.py` returns zero matches.)

### User paths

Every user-supplied file path is wrapped in `os.path.abspath(os.path.expanduser(path))` before being passed to a subprocess. This neutralizes the historical "flag injection" concern (e.g. a path starting with `-` being interpreted as a CLI flag).

### yt-dlp cookie and remote-components flags

`--cookies-from-browser` and `--remote-components` are **off by default** in `~/.cli-studio/config.json`. Both can be enabled from the Settings menu (`/settings` or `Alt+S`). The "Cookies" setting accepts a browser profile name (e.g. `chrome`, `firefox`, `chrome:Default`); `yt-dlp` then reads that browser's cookie database on demand.

### Input validators

Numeric and structured text inputs are validated against regex patterns before they reach ffmpeg/imagemagick/exiftool/rclone:

- `validate_resolution` (`W:H` like `1280:-1`)
- `validate_dimensions` (`WxH` like `1920x1080`)
- `validate_coords` (`L,T,R,B` like `0,0,500,500`)
- `validate_decimal` (positive number)
- `validate_remote_name` (rclone remote name, no flags)
- `validate_exif_tag` (EXIF/XMP tag name, no flag prefix)
- `validate_cache_dir` (path under `$HOME`, `/tmp`, or `/var/tmp`)

Invalid input raises `ValueError`, which the wizard catches and displays as a toast notification. The wizard modal stays open so the user can fix the input.

### Atomic config writes

`config._save_config` writes to a temporary file via `tempfile.mkstemp()` then `os.replace()`. Either the old config or the new config survives a crash — never a half-written file. Verified by reading the source.

### Markup injection

Output strings that mix Rich markup with user-controlled data call `rich.markup.escape()` on the user-controlled portion. Three sites in `cli-studio.py:_update_output` and five in `ui/progress.py` were hardened in the 2026-07-21 audit (Phase 8). The "Unknown command" toast at `cli-studio.py:680` uses `log_palette_colors(self.active_theme)` for its colour so it stays consistent with the active theme.

### Wizard exception handling

`_BaseInputModal._submit` maps exception types to user-facing toasts instead of leaking raw traceback text:

- `ValueError` → "Invalid input. Check the format and try again."
- `FileNotFoundError` → "File not found: <path>"
- `OSError` → "File system error: <reason>"
- Any other `Exception` → "Unexpected error; press '?' for help." (full traceback goes to `logger.exception()`)

The wizard modal stays open so the user can fix the input.

### `burn subtitles` filter escaping

The `burn subtitles` wizard escapes backslash, single quote, colon, square brackets, comma, and semicolon in the subtitle path before embedding it in the ffmpeg `subtitles=` filter. Paths containing these characters no longer break the filter parser.

### Plugin execution

Any `.py` file in `~/.cli-studio/plugins/` is loaded with the full privileges of the cli-studio process. **This is by design.** If you sync that directory with another machine, you are trusting that machine's plugin directory contents. Built-in commands cannot be overwritten by plugins (collisions silently lose).

---

## What cli-studio does NOT promise

### `curl | bash` install pattern

`README.md` recommends `curl -fsSL https://cso.codefxr.com/install | bash`. This is the **user's stated preference** despite the broader hygiene community's "inspect before you pipe" guidance. The cli-studio source tree at `cli-studio/install` is a bash script that:

- Installs system packages via `apt`, `dnf`, `pacman`, or `brew` (with `sudo`).
- Clones the repo into `~/.cli-studio/`.
- Sets up an isolated Python virtual environment.
- Creates `cli-studio` and `cso` symlinks in `~/.local/bin/`.
- Optionally appends `export PATH=...` to your shell RC file **after** printing the diff and asking for confirmation (as of 2026-07-21).

Reviewers are encouraged to read `cli-studio/install` before running it. The script is plain bash and ~225 lines.

### `pip install .` entry point

`pyproject.toml` declares `[project.scripts]` with `cli-studio` and `cso` entry points that call `cli_studio:main()` (a thin shim around the live module at `cli-studio.py`). Installing via pip is supported, but the bash install script is the recommended route because it sets up the venv and system-package dependencies in one step.

### ffmpeg / yt-dlp / etc. as root

If you run cli-studio as root (e.g. via `sudo`), all subprocess commands also run as root. cli-studio does not warn about this. It is the user's responsibility to know whether their files and system can tolerate root-level tool execution.

### Plugin directory trust

`~/.cli-studio/plugins/*.py` files execute with your user privileges. Treat that directory like `~/.ssh/`: don't let untrusted sources write to it.

### ffmpeg overwrite default

The `ffmpeg_overwrite` setting defaults to `True` (the `-y` flag), so ffmpeg will silently overwrite existing files. Toggle it off in Settings if you'd rather be prompted.

### Network calls

yt-dlp and gallery-dl make outbound network calls to the URL you provide. The default yt-dlp `--js-runtimes node` flag means downloads may reach GitHub for EJS challenge solvers when required. cli-studio does not phone home independently.

---

## Reporting issues

Open a GitHub issue at https://github.com/codefxr/cli-studio/issues. Mark security-relevant bugs with the `security` label.

For sensitive disclosures, contact the maintainer directly via the address on the GitHub profile. (Update this section when a security@ alias is established.)