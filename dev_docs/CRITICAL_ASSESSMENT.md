# CLI-Studio — Critical Assessment

> **Purpose.** Outside opinion from a senior-dev / user perspective. Not a code review by the project's own author.
> **Date.** 2026-07-15
> **Perspective.** A senior developer who has not written this codebase, reviewing it cold. Plus the perspective of someone who would actually try to use the app day-to-day.
> **Project.** `/home/jvm/projects/cli-studio/`
> **Codebase size at time of audit.** ~1,854 LOC of project Python (excluding `.venv/`), 267 LOC of CSS, ~85 lines of bash installer, plus 7 `.md` docs.
> **See also.** `CRITICAL_ASSESSMENT_part2.md` (2026-07-21, score 8.5) and `CRITICAL_ASSESSMENT_part3.md` (2026-07-22, score 9.3) for the subsequent passes that brought the project to its current state.

---

## TL;DR — Score: **6.5 / 10**

CLI-Studio is a real, working TUI that wraps 37+ ffmpeg/yt-dlp/Pillow/ImageMagick/ExifTool operations behind a Textual interface with batch processing, themes, and a help system. The modular architecture (`workflows/` + `ui/`) is sound and the registry pattern is textbook. **But** the codebase is showing clear signs of unmoderated AI-assisted development: a committed one-shot patch script (`patch_system.py`), bare `except: pass` clauses, hallucinated dependency versions, copy-pasted CSS that should be data-driven, and marketing-tone documentation that oversells the current state. There are also real security concerns (forced Chrome cookie extraction, GitHub network dependency, markup injection in user-facing strings, `curl | bash` install).

The June-2026 "Code Reality Audit" in `AGENTS.md` rates cli-studio 7/10 (matches the project's own self-assessment in `README.md`). My read is honest but slightly stricter because the artifact evidence is damning. The current code works for its stated use case; it does not need to be rewritten. It needs to be **cleaned, hardened, and one-shot-patched to maturity**.

---

## 1. What the project claims vs. what is in the tree

| Claim | Reality |
|---|---|
| "37+ Integrated Tools" | 37 entries in `COMMAND_REGISTRY`; matches the menus. Real. |
| "Auto-Batch Processing" | Implemented for FFmpeg and Pillow (folder detection in `ui/progress.py`). Audio batch works only via shared flows (`build_convert_media_flow`, `build_trim_media_flow`). **Not all 37 tools support batch** — `build_exiftool_strip_flow`, `build_imagemagick_filter_flow`, `build_remove_bg_color_flow` do not iterate over folders. |
| "Smart Input Autofill (ffprobe)" | `workflows/utils.py:get_media_duration` is wired into trim flows only. **Truncates fractional seconds** — `00:03:15.7` → `00:03:15`. Sub-second pre-fill is wrong. |
| "Power User Log Console (Ctrl+L)" | Implemented in `ui/progress.py`. **Batch FFmpeg/Pillow operations log nothing** — `subprocess.DEVNULL` for stdout/stderr in the batch branch (`progress.py:149`, `progress.py:336`). The "Power User" log is single-file-only. |
| "Integrated Help System (?)" | `HELP_REGISTRY` in `config.py` has **14 entries for 37 tools**. The fallback message is generic. |
| "8 themes" | 8 themes present, but **theme names drift** between `README.md` ("Modern, Hunter, Coppice, Navy, Pink, Bleu Gris, Too Modern, Original") and `studio_themes.py` (`"t-accident": "navy"` — the key is "accident", the display name is "navy"). Confusing. |
| "37 distinct, fully-integrated capabilities" | Mostly true; one notable regression: **subtitles are "extracted" but `extract subtitles` ignores batch paths** — there is no folder-batch version. |
| "Anti-Flag Injection (os.path.abspath)" | Real for FFmpeg/Pillow paths. **But not for yt-dlp flags**: `yt-dlp --cookies-from-browser chrome --js-runtimes node --remote-components ejs:github` is hardcoded; user-provided URL is `--`-separated but not all user inputs are validated (e.g., the `--no-playlist` flag could be flipped by a URL with `--` in it). |

---

## 2. Architecture review

### 2.1 What works

- **Command registry pattern** (`workflows/registry.py:3`) — clean dict dispatch, easy to extend. Each tool is a builder function that returns the next ModalScreen. Good separation.
- **Step-state pattern** — `state = {}` dict threaded through nested closures is a pragmatic solution for Textual's modal stack. Works.
- **Worker threading** — `run_worker(thread=True, exclusive=True)` keeps the TUI responsive. Cancellation token (`worker.is_cancelled`) is checked in the right places.
- **Theme engine** — `THEME_ORDER` + `THEME_NAMES` + `NAME_TO_CLASS` is a sensible data-driven approach at the Python level. The CSS, however, is not data-driven (see §3.3).
- **`build_download_flow(is_audio, is_playlist)`** — parameterizing three "Download" tools into one builder is the right abstraction.

### 2.2 What doesn't work

- **`view_stack` is half-implemented.** `push_view`/`pop_view` exist, but `pop_view` falls back to `"home"` when the stack is empty — and you can never get to a stack depth > 1 in normal navigation because each `_switch_to` clears the view classes. The stack is essentially dead code. Either remove it or use it.
- **`menu_context` state machine is convoluted.** Switching from `/video` → `/audio` → `/themes` requires three places to stay in sync (`_switch_to`, `on_input_submitted`, `action_show_menu`). The same logic is duplicated 4× in `on_input_submitted` (`cli-studio.py:425-439`).
- **Modal flow leaks exceptions to the user.** `on_input_submitted` in all three modal screens wraps the next-step call in `try: ... except Exception as e: self.app.notify(str(e))`. User-visible tracebacks via `str(e)` for things like `int("hello")` are noisy.
- **`apply_theme` mutates both App and Screen classes.** Adds the theme class to `self` AND `self.screen` — twice. Pick one. Putting it only on `Screen` is what 90% of Textual apps do.

---

## 3. AI signatures & code smells

The following are the strongest tells that cli-studio has been built with significant unmoderated AI assistance. Each is fixable.

### 3.1 `patch_system.py` (CRITICAL — committed to the tree)

This file is the single most damning artifact in the project. It is a one-shot Python script that opens source files and overwrites them with hardcoded code blocks:

```python
# patch_system.py
import os
with open('/home/jvm/projects/cli-studio/config.py', 'a') as f:
    f.write('''\n
HELP_REGISTRY = {
    "download video": "...",
    ...
}
def get_help(cmd):
    return HELP_REGISTRY.get(cmd, f"Runs the '{cmd}' tool...")
''')
```

This is a chat-session artifact. It is the kind of script an LLM suggests when a user says "patch these files" mid-conversation, then the user runs it once and forgets to delete it. **It is not a build step, not a test, not documentation.** It is dead code that, if re-run, would corrupt the project (e.g., `config.py` would get a second `HELP_REGISTRY` appended after the first one).

**Action:** delete the file. Move on. Verify the patched-in code (the `HELP_REGISTRY` block, the `workflows/utils.py:get_media_duration`, the `write_log` method on `DownloadProgressScreen`) matches what's actually live — those patches have already been applied to the tree and need to stay.

### 3.2 Bare `except: pass` clauses

Six occurrences in the project source (excluding `.venv/`):

```
patch_system.py:93        except: pass
cli-studio.py:168         except: pass
cli-studio.py:180         except: return default
ui/progress.py:25         except: pass
ui/progress.py:110        except: pass
ui/progress.py:206        except: pass
ui/screens.py:70          except: pass
```

This is the classic "AI handles errors by swallowing them" pattern. Every one of these can be replaced with a specific exception type and a real log call. Bare `except:` also catches `KeyboardInterrupt` and `SystemExit`, which is a separate bug.

### 3.3 Copy-pasted CSS in `studio_themes.py`

The `THEMES_CSS` string is 136 lines of structurally identical CSS — 8 themes × 17 selectors each, where only the colors change. The right structure is:

```python
PALETTES = {
    "t-default": {"bg": "#1e1e2e", "panel": "#24283b", "border": "#414868",
                  "logo": "#00a9ae", "accent": "#00dadf", "text": "#c0caf5"},
    ...
}

def _css_for(name, p): return f"""
Screen.{name} {{ background: {p['bg']}; }}
.{name} #input-container {{ background: {p['panel']}; border: tall {p['border']}; }}
...
"""
THEMES_CSS = "\n".join(_css_for(n, PALETTES[n]) for n in THEME_ORDER)
```

That collapses 136 lines to ~40, and adding a theme becomes a 1-line dict entry instead of a 17-line copy-paste block.

### 3.4 `write_log` duplicated 3× in `ui/progress.py`

Identical 4-line methods at `progress.py:21`, `:106`, `:202`. Should be a mixin on a shared `_LoggingModalScreen` base class. (Once `patch_system.py`'s additions are merged, all four progress screens will have it.)

### 3.5 Inline color markup hardcoded

`f"[bold #00dadf]Executing:[/bold #00dadf] {' '.join(cmd)}"` appears twice (`progress.py:171`, `:227`). The color `#00dadf` is one theme's accent; if the user is on a different theme, the log line still shows teal. Should derive from the active theme's accent palette.

### 3.6 Section-marker comments

`# BATCH PROCESSING LOGIC`, `# SINGLE FILE LOGIC`, `# PDF EXPORT LOGIC`, `# BATCH LOGIC` in `ui/progress.py`. These are AI-generated "explain what I'm doing" comments — they don't add information beyond what the next 3 lines obviously do. Per AGENTS.md: no comments unless asked.

### 3.7 Pillow imported inside the method

`process_image` does `from PIL import Image, ImageOps, ImageDraw` at line 267. `Pillow` is already in `requirements.txt`; should be a module-level import. Same for `from PIL import Image` at line 289. This is the kind of lazy import an AI adds because it doesn't want to think about import-time cost — but Pillow import is cheap and Textual handles app startup separately.

### 3.8 Hallucinated dependency versions in `requirements.txt`

```
textual>=8.2.5
textual-image>=0.12.0
Pillow>=12.2.0          # ← Pillow 12.x does not exist as of mid-2026 (latest is 10.x)
yt-dlp>=2026.3.17       # ← date-based version that does not yet exist
```

The other two (`textual`, `textual-image`) are plausible. **These last two will make `pip install -r requirements.txt` fail** for any user. This is a release blocker. Either pin to real versions (`Pillow>=10.4.0,<11`, `yt-dlp>=2025.5.22`) or write a `setup.cfg`/`pyproject.toml` with sane upper bounds.

### 3.9 Marketing-tone documentation

```
"the definitive terminal media app for both beginners and power users"
"The Ultimate Terminal Media Dashboard"
"Massive Polish & Quality of Life Update (March 2026)"
"Power User Log Console"
"Smart Input Autofill"
"A massive suite of media manipulation utilities out-of-the-box."
```

This is the LLM writing a launch announcement, not a maintainer writing engineering notes. It is fine for a product website. It is not fine for an in-tree `ARCHITECTURE.md`. The same drift appears in `PROGRESS.md` ("Massive Update (March 2026)") and `website_docs.md` ("Ultimate", "37+").

### 3.10 Inconsistent exception handling in `write_log`

`write_log` wraps `self.app.query_one("#terminal-log")` in `try: ... except: pass`. The right fix is to use `self.app.query_one("#terminal-log", expect_type=None)` or `try: ... except NoMatches: pass` — bare `except` hides every error, including a typo in the widget ID.

---

## 4. Security review

### 4.1 High

1. **`--cookies-from-browser chrome` is hardcoded** (`ui/progress.py:54`). This is a privacy-invasive flag: yt-dlp will read Chrome's cookie database on every run. It will also fail on machines that don't use Chrome, and silently fail if Chrome's cookie DB is encrypted (which it is by default on modern Linux). There is no consent prompt. **Move to a setting.**

2. **`--remote-components ejs:github` is hardcoded** (`ui/progress.py:54`). This makes cli-studio's YouTube flow dependent on GitHub network access at every run. If GitHub goes down (or the user's network blocks it), downloads fail for many sites. **Make this opt-in via a setting.**

3. **`curl ... | bash` is the recommended install** (`README.md:57`). Per AGENTS.md Pipeline Hygiene Rule 3, this is the anti-pattern. The `install` script is well-written but the recommended distribution mechanism undermines any audit of what gets installed.

4. **No sandboxing on subprocess args.** While subprocess is called with `list` (no `shell=True`), `self.action_args` are passed to ffmpeg as `list[str]` without validation. The list is constructed in `workflows/*.py` from user input (e.g., `state['res']` in `build_scale_video_flow` is interpolated into an ffmpeg filter string: `f"scale={state['res']}"`). A user entering `1280:-1; rm -rf ~` won't shell-inject (because `shell=False`), but they can inject ffmpeg filter syntax that crashes the run or produces garbage. **Validate inputs against `^[0-9:-]+$`** for numeric fields.

5. **Output markup injection.** `cli-studio.py:451` builds a Rich markup string with user input:
   ```python
   self._update_output(f"[bold #f7768e]Unknown command:[/bold #f7768e] {cmd}")
   ```
   If a user types `/foo[/bold]`, the markup breaks and the rest of the line renders wrong. Either escape with `rich.markup.escape` or use the `markup=False` flag on `Static.update`. **Same pattern in `ui/progress.py:171, :227`.**

6. **`ffmpeg -y` always overwrites.** No "file exists, overwrite?" prompt. Acceptable for a power-user tool but should be a setting (and is called out in #1 of any user-facing FAQ).

### 4.2 Medium

7. **Config write is not atomic.** `cli-studio.py:182` opens `~/.cli_studio_config.json` for write directly. If the process is killed mid-write, the file is corrupted and the next launch fails (caught by the bare `except`, so it silently falls back to default theme). Use a temp-file + `os.replace()` pattern.

8. **`get_media_duration` uses `timeout=1` second** (`workflows/utils.py:9`). Tight. Slow filesystems or NFS shares will throw `TimeoutExpired`. The function falls back to `"00:01:00"` which is wrong for a 3-hour video.

9. **`exiftool -all=` runs without `-overwrite_original` flag.** This means exiftool creates `<file>_original` files next to every input. Users running this on a folder get N duplicate files they didn't expect. Document or default to `-overwrite_original`.

10. **`--js-runtimes node` is required** but `node` is not installed by the install script. On distros where Node isn't preinstalled, every yt-dlp run will warn or fail for sites that need JS challenge solving.

11. **No size limit on batch conversions.** User can fill their disk by selecting a large folder as input. No `quota` or `confirm total: X MB, proceed?` step.

### 4.3 Low / informational

12. **No input path validation.** `os.path.abspath(os.path.expanduser(path))` prevents some flag injection but not all (e.g., `~/../../etc/passwd`). This is fine because the user is consenting to the operation, but worth noting.

13. **`ffmpeg` is invoked as the unqualified binary.** A user with a malicious `ffmpeg` earlier in `$PATH` (e.g., in `~/bin`) will have that binary run instead of the system one. Not cli-studio's problem; just be aware.

14. **`subprocess.run(..., timeout=1)` for `ffprobe` will swallow the result if the file is on a slow disk.** Catch `TimeoutExpired` explicitly.

15. **`mojibake risk in user-visible strings.** Rich markup injection is the main risk; if the user pastes binary into a label, it could render as escape codes. Mitigated by Rich's default safety but worth testing.

---

## 5. Refactor opportunities (shorten & dedup)

These are pure code-quality wins, no behavior change.

### 5.1 Modal screens share a base class

`ui/screens.py` has three modal screens (`TextInputScreen`, `FilePickerScreen`, `OptionSelectScreen`) with three nearly identical `on_input_submitted` / `on_option_list_option_selected` handlers (lines 31-42, 83-94, 119-127). The handler logic is:

```python
val = event.value.strip() or self.default_val
if not val:
    self.app.notify("Input cannot be empty", severity="error")
    return
try:
    next_screen = self.next_step_func(val, self.state)
    self.dismiss()
    if next_screen:
        self.app.push_themed_screen(next_screen)
except Exception as e:
    self.app.notify(str(e), severity="error")
```

Extract to a `_BaseInputModal(ModalScreen)` with a `_handle_submit(value)` method. Three classes shrink from ~40 lines each to ~15.

### 5.2 Dispatch table for `/command` parsing

`cli-studio.py:421-441` is a 21-line `if cmd == "/home": ... elif cmd == "/video": ...` chain. Replace with:

```python
COMMANDS = {
    "/home": lambda s: s.action_go_home(),
    "/back": lambda s: s.action_go_back(),
    "/about": lambda s: s.action_show_about(),
    ...
    "/video": lambda s: s._enter_menu("video"),
    "/audio": lambda s: s._enter_menu("audio"),
    "/image": lambda s: s._enter_menu("image"),
    "/themes": lambda s: s.action_show_themes(),
    "/exit": lambda s: s.action_show_exit(),
}
```

Then `cmd, _, arg = value.partition(' '); COMMANDS.get(cmd, lambda s: s._unknown(cmd))(self)`. The `/video | /audio | /image` triple becomes a single `_enter_menu(name)` method.

### 5.3 Theme CSS from a palette dict

See §3.3. ~95-line reduction in `studio_themes.py`.

### 5.4 Logging mixin for progress screens

See §3.4. ~12-line reduction.

### 5.5 Workflow builder boilerplate

Every `build_*_flow` function in `workflows/video.py`, `audio.py`, `image.py`, `shared.py` follows the same pattern:

```python
def build_X_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        ... derive defaults ...
        return FilePickerScreen(...) or OptionSelectScreen(...) or TextInputScreen(...)
    def step3(...):
        ...
    return FilePickerScreen("Select Media File/Folder:", "", {}, step2)
```

The pattern "input → save picker → progress screen" is ~70% of the codebase. A higher-order helper like:

```python
def file_in_out_flow(tool_name, action_args, target_ext=None, save_suffix=""):
    def step2(in_file, state):
        state['in_file'] = in_file
        base, ext = os.path.splitext(in_file)
        return FilePickerScreen("Save As:", f"{base}_{save_suffix}{ext}", state, step3)
    def step3(out_file, state):
        return FfmpegProgressScreen(state['in_file'], out_file, action_args, target_ext=target_ext)
    return FilePickerScreen(f"Select {tool_name} File/Folder:", "", {}, step2)
```

Would collapse ~10 video/audio flows to one-liners. The `is_video`/`is_audio` parameters in `build_trim_media_flow` and `build_convert_media_flow` would survive as the only complex cases.

### 5.6 `view_stack` removal

If the stack is only used for back-button semantics and never reaches depth > 1 in practice, delete it. Back goes to home. Saves ~20 lines and removes a class of "stale view state" bugs.

### 5.7 `apply_theme` — pick App or Screen, not both

Pick `Screen`. Removes 1 line of state and 1 source of bugs.

### 5.8 `RichLog` writing helper

Three progress screens write to `#terminal-log`. Centralize:

```python
def write_to_log(text: str) -> None:
    try:
        self.app.query_one("#terminal-log").write(text)
    except Exception:
        pass
```

As a function in `ui/progress.py` (or a static method on a mixin).

---

## 6. Bugs (real, not stylistic)

1. **`get_media_duration` truncates fractional seconds** (`workflows/utils.py:13-14`). `int(duration % 60)` floors to whole seconds. For a 1h 23m 45.7s video, the pre-filled end time is `01:23:45` — the user can never trim to the true end.

2. **Trim batch flow output paths collide.** `build_trim_media_flow` builds `f"{base}_trimmed{ext}"`. In batch mode, every input file produces `name_trimmed.ext` in the same output dir — fine if names are unique, but if two folders both contain `clip.mp4`, the second overwrites the first. (Same problem in every flow that derives a default output name from the input stem.)

3. **`PillowProgressScreen.run_pillow` PDF branch silently does nothing if the input folder has no images.** `if not files: return` (line 296) — no notify, no dismiss. The user sees the progress dialog hang forever.

4. **`build_images_to_pdf_flow` sorts images alphabetically** (`progress.py:295`). `1.png, 10.png, 2.png` sorts to `1.png, 10.png, 2.png` — wrong page order. Use `natsort` or a small natural-sort key.

5. **`utils.get_media_duration` returns `"00:01:00"` on every error.** Including file not found, ffprobe missing, JSON parse error, division by zero, timeout — same fallback. Means the user gets a misleading default and the trim is wrong. Should at least notify.

6. **Batch processing for FFmpeg swallows ffmpeg errors** (`progress.py:149`). `subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)` — no check of `returncode`. A failed file looks identical to a successful file in the batch progress UI.

7. **`PillowProgressScreen.process_image` ignores the `convert` action** for images. The batch "convert" flow uses `target_ext` and saves as the new format, but the single-file `process_image` doesn't validate mode conversion for non-RGB targets. If the user converts a PNG to JPG with transparency, the alpha is silently dropped by Pillow's default save (no `convert("RGB")` in the single-file path).

8. **Theme CSS file misses the `#about-panel { padding: 0 2 }` rule.** The `#about-text` rule has it, but `#about-panel` itself doesn't, so long About text butts against the panel border.

9. **`CommandSuggester.get_suggestion` returns the suggestion for `/themes` only when prefixed.** `value.startswith("/")` returns `None` for empty value, but `value.startswith("/themes/")` will match `/themes` without the trailing slash only inside the second branch. So `/themes` (no slash, no name) shows no suggestion but typing `/themes/p` shows one. Inconsistent.

10. **`apply_theme(theme_class=...)` is called with the raw string but `THEME_ORDER` contains strings.** Fine in practice; but if the user types a malformed theme name in `/themes/foo`, the second `_apply_theme_by_name` falls through to the substring match (lines 213-217) which has its own edge case: `if len(matches) == 1` succeeds, but multiple matches just returns `None` — silent failure.

11. **`build_extract_subs_flow` has no folder batch.** Other video flows do. Inconsistent.

12. **`--no-playlist` flag is forced for single video.** This is the right default, but means `yt-dlp https://youtube.com/watch?v=ID&list=PLAYLIST` will only download the one video. Users who paste a playlist URL into the single-video tool will be confused. Should at least detect playlist URLs and prompt.

13. **`on_mount` of the App notifies `Missing 'textual-image' lib.`** at warning level. This is fine but the fallback to ASCII art logo is acceptable — the warning fires every launch and trains users to ignore it.

---

## 7. Documentation drift

| File | Says | Reality |
|---|---|---|
| `README.md` | 8 themes: Modern, Hunter, Coppice, Navy, Pink, Bleu Gris, Too Modern, Original | `studio_themes.py` has 8 themes with key names `t-default, t-modern, t-too-modern, t-coppice, t-hunter, t-accident, t-bleu-gris, t-pink`. The "accident" key has display name "navy". **The list order also disagrees.** |
| `README.md` | "37+ Integrated Tools" | Exactly 37 in `COMMAND_REGISTRY`. The "+" is forward-looking. |
| `docs.md` | "Alt+a About" binding | Yes, present. |
| `docs.md` | "Alt+m Menu, Alt+t Themes, Alt+b Back, Alt+e Exit" | Yes. |
| `docs.md` | "Ctrl+c Quit" | Yes. |
| `docs.md` | No mention of `?` help key | `?` IS bound in `cli-studio.py:143`. The help docs are out of sync. |
| `PROGRESS.md` | "37 unique, fully-integrated capabilities" | 37 in registry. "Fully-integrated" is generous — see §1. |
| `ROADMAP.md` | "Hardware Accelerated Encoding" (NVENC, VideoToolbox) | Not implemented. |
| `ROADMAP.md` | "Burn Subtitles (Hardsubs)" | Not implemented. |
| `ROADMAP.md` | "EXIF Metadata Editor" | Not implemented (only stripper). |
| `ARCHITECTURE.md` | "Worker Threading (`run_worker(thread=True)`)" | Correct. |
| `website_docs.md` | Distributing the codebase under `/home/jvm/projects/cli-studio/` | Wrong; this is the install location, not the docs. The docs are confusing on first read. |

---

## 8. Recommended roadmap (ordered by ROI)

### 8.1 Tier 1 — Hardening (must do before next release)

| # | Task | Why | Estimated effort |
|---|---|---|---|
| 1 | **Delete `patch_system.py`.** | Committed dead code; AI artifact. | 5 min |
| 2 | **Fix `requirements.txt` versions** — replace `Pillow>=12.2.0` with `Pillow>=10.4.0,<11` and `yt-dlp>=2026.3.17` with a real version like `yt-dlp>=2025.5.22`. | Releases are broken right now. | 5 min |
| 3 | **Move `--cookies-from-browser chrome` and `--remote-components ejs:github` to settings** with a default-off toggle. | Privacy + offline-friendliness. | 2 hours |
| 4 | **Atomic config write** (`tempfile + os.replace`) | Prevents corrupted config on kill. | 30 min |
| 5 | **Escape user input in `update_output` markup.** Use `rich.markup.escape` or pass `markup=False`. | Closes output injection. | 30 min |
| 6 | **Catch `TimeoutExpired` in `get_media_duration`** and notify instead of returning the silent fallback. | UX fix. | 15 min |
| 7 | **Fix `get_media_duration` truncation** — preserve milliseconds or at least round, don't floor. | Trim pre-fill is wrong on fractional-second videos. | 15 min |
| 8 | **Replace all 6 `except: pass` with specific exceptions.** | AI smell; also catches `KeyboardInterrupt` and `SystemExit` (real bug). | 1 hour |
| 9 | **Validate numeric inputs** (resolution, volume, speed, fade) against regex before passing to ffmpeg. | Defense in depth. | 1 hour |
| 10 | **Fix `PillowProgressScreen` "no images in folder" silent return** — notify and dismiss. | UX bug. | 15 min |
| 11 | **Fix batch `convert image` transparency loss** — add `convert("RGB")` for non-PNG targets in single-file path. | Bug. | 15 min |
| 12 | **Natural sort for PDF assembly.** | Correctness. | 15 min |
| 13. | **Add `--no-playlist` warning or playlist-URL detection.** | UX clarity. | 30 min |

### 8.2 Tier 2 — Dedup & refactor (clean engineering)

| # | Task | Why |
|---|---|---|
| 14 | **Theme CSS data-driven** (palette dict + template). | -95 LOC. |
| 15 | **`_LoggingModalScreen` mixin** for the four progress screens. | -12 LOC. |
| 16 | **`_BaseInputModal` base class** for the three input modals. | -75 LOC. |
| 17 | **Command dispatch table** for `/command` parsing. | -20 LOC. |
| 18 | **`file_in_out_flow` helper** for the common "input → save picker → progress" pattern. | -200 LOC across `workflows/*.py`. |
| 19 | **Remove dead `view_stack`** OR use it properly. | Removes class of bugs. |
| 20 | **Theme-aware log colors.** Derive `[bold]Executing:[/bold]` accent from the active theme. | Consistent look. |
| 21 | **Pillow imports at module level.** | Conventional. |
| 22 | **Rewrite README & docs tone.** Replace marketing language with engineering language. | Honest signal of maturity. |
| 23 | **Add a `CONTRIBUTING.md` + `tests/` skeleton.** | Currently zero tests. The only "test" is `python cli-studio.py` works. |
| 24 | **Add `pyproject.toml`** with proper metadata and pinned deps. | Replaces bare `requirements.txt`. |
| 25 | **Add CI** (GitHub Actions: ruff + mypy + pytest). | The other v1.0 projects have nothing either, but cli-studio is the closest to ready. |

### 8.3 Tier 3 — Feature additions (ROADMAP.md alignment)

The existing `ROADMAP.md` lists aspirational features. Tier 3 is "actually ship one." Ordered by ROI:

| # | Task | ROI | Effort |
|---|---|---|---|
| 26 | **Wrap `pandoc`** — add a "Documents" tab. New file `workflows/documents.py`. | High (universal use case) | Low |
| 27 | **Wrap `qpdf`** — merge / split / encrypt. | High (common need) | Low |
| 28 | **Wrap `tesseract`** — "Extract Text from Image". | Medium | Low |
| 29 | **Wrap `HandBrakeCLI`** — "Device Presets" tab. Bigger feature surface than ffmpeg's default CRF. | High | Low |
| 30 | **Wrap `mkvmerge`/`mkvextract`** — remux without re-encoding, extract subs/attachments. | Medium | Low |
| 31 | **Wrap `gallery-dl`** — image gallery download. | Medium | Low |
| 32 | **Wrap `chafa`** as an in-TUI image preview pane (terminal-native). | High UX win | Medium |
| 33 | **Wrap `audiowaveform`** + chafa for waveform preview. | Medium | Medium |
| 34 | **Wrap `rclone`** for cloud upload of finished files. | Medium | Low |
| 35 | **Wrap `whisper.cpp`** (or `faster-whisper`) for auto-subtitle generation. | High (podcasters love this) | Medium |
| 36 | **Add hardware-accel codec selection** (NVENC/VideoToolbox/VAAPI) — ROADMAP §1. | Medium | Medium |
| 37 | **Add burn-subtitles (`subtitles=` filter)** — ROADMAP §1. | Medium | Low |
| 38 | **Add spritesheet/montage** (`magick montage`) — ROADMAP §1. | Medium | Low |
| 39 | **EXIF metadata editor (write, not just strip)** — ROADMAP §1. | Medium | Low |
| 40 | **Green-screen chroma key** — ROADMAP §1. | Low (niche) | Low |
| 41 | **AI image upscaling** — upscayl-ncnn wrapper. | Medium | Medium (Vulkan dep) |
| 42 | **Silence removal** (`silenceremove` filter) — ROADMAP §1. | Medium | Low |
| 43 | **Audio visualizer generation** (`showwaves`) — ROADMAP §1. | Low (niche) | Low |
| 44 | **Cloud upload via `rclone`** — ROADMAP §2. | Medium | Low |
| 45 | **Picture-in-Picture** — ROADMAP §1. | Low (niche) | Medium |

### 8.4 Tier 4 — Architectural improvements (v2.0 thinking)

| # | Task | Notes |
|---|---|---|
| 46 | **Add a real test suite.** Today there are no tests. The Textual `Pilot` framework supports headless UI tests. Mock subprocess calls. |
| 47 | **Move from `requirements.txt` to `pyproject.toml`** with optional-deps groups (`[ffmpeg]`, `[ocr]`, `[cloud]`, `[ai]`). Lets users install only the backends they want. |
| 48 | **Pluggable backend abstraction.** Today `magick` is called directly; tomorrow it could be a `Backend` interface with `ImageMagickBackend` and `PillowBackend` implementations. Same for `yt-dlp` (could swap for `gallery-dl` or `you-get`). |
| 49 | **Settings screen.** Currently every global is a constant. Need a settings screen for cookies, remote-components, theme persistence, ffmpeg overwrite defaults, etc. |
| 50 | **Plugin system.** A `~/.cli-studio/plugins/` directory of `.py` files that register additional tools in `COMMAND_REGISTRY`. This is the only way the 37-tool surface stays manageable as it grows. |

---

## 9. Competitive landscape (web research, July 2026)

Stars and repo data verified via direct GitHub fetches.

### 9.1 Direct TUI competitors (you should know they exist)

| Tool | URL | Stars | Stack | Relevance |
|---|---|---:|---|---|
| **xytz** | https://github.com/xdagiz/xytz | 528 | Go + Bubble Tea | Best-looking YouTube TUI. Vim keys, thumbnails. cli-studio's YouTube tab overlaps. |
| **ytfzf** | https://github.com/pystardust/ytfzf | 4.1k | POSIX shell + fzf + mpv | De-facto YouTube TUI. Last release 2024-01 — stale. UX reference. |
| **yt-x** | https://github.com/Benexl/yt-x | 1.6k | POSIX shell + fzf | 1500+ sites, subscriptions. Don't compete; cite in docs. |
| **ytsurf** | https://github.com/Stan-breaks/ytsurf | 499 | Bash + fzf | Syncplay (watch with friends). cli-studio has no equivalent. |
| **Feather** | https://github.com/13unk0wn/Feather | 234 | Rust + Ratatui | YouTube Music streaming (no download). Low-resource UX reference. |
| **vic** | https://github.com/wong-justin/vic | 128 | Rust + crossterm + chafa | Trim/cut video with frame-accurate markers. Most directly relevant UX competitor — uses chafa for in-terminal preview. **cli-studio should ship with chafa and add a preview pane.** |
| **ffdash** | https://github.com/bcherb2/ffdash | 64 | Rust + Ratatui | AV1/VP9 batch encoder with HW accel. SSH-friendly. |
| **webvids** | https://github.com/henrygd/webvids | 67 | Go + Bubble Tea | One-job TUI: video → AV1/x265 web-optimized. Opinionated preset UX. |
| **visualvault** | https://github.com/mikeleppane/visualvault | 63 | Rust + Ratatui | Smart date-based media organizer with EXIF extraction, duplicate detection, undo/redo. Niche but polished. **Borrow the undo system and EXIF card.** |
| **SubForge** | https://github.com/yumiaura/SubForge | 16 | Python + Textual + faster-whisper | Most direct ROADMAP overlap: media → subtitles → translation → mux → burned-in. Same Textual stack. **Sibling project, possible upstream consolidation.** |
| **ytcon** | https://github.com/NikitaBeloglazov/ytcon | 25 | Python + Urwid | Closest Python YouTube-TUI competitor. Urwid (not Textual). |
| **effy** | https://github.com/aNNiMON/effy | 14 | Rust + crossterm | Friendly minimal ffmpeg helper. |
| **docufy** | https://github.com/mlihgenel/docufy | 11 | Go | Watch-folder mode for transcoding — cli-studio could add this. |

### 9.2 CLI tools worth wrapping (extends the existing ROADMAP)

Already on ROADMAP.md (*) and worth confirming with current data:

| Tool | URL | Stars | Latest release | Notes |
|---|---|---:|---|---|
| **pandoc** * | https://github.com/jgm/pandoc | 45.4k | Jun 2026 | "Documents" tab. |
| **qpdf** * | https://github.com/qpdf/qpdf | 5.2k | 12.3.2 (Jan 2026) | PDF merge/split/encrypt. |
| **tesseract** * | https://github.com/tesseract-ocr/tesseract | 75.4k | 5.5.2 (Dec 2025) | OCR. 100+ languages. |
| **whisper.cpp** * | https://github.com/ggml-org/whisper.cpp | 51.8k | v1.9.1 | Local ASR. Note: SubForge uses `faster-whisper` (Python binding) — friendlier. |
| **rclone** * | https://github.com/rclone/rclone | 58.3k | v1.74.4 (Jul 2026) | 70+ cloud backends. |
| **gallery-dl** * | https://github.com/mikf/gallery-dl | 18.9k | v1.32.6 (Jul 2026) | Note: migrating from GitHub to Codeberg — pin Codeberg URL for installs. |
| **upscayl** * | https://github.com/upscayl/upscayl | 47.2k | — | Wrap the CLI `upscayl-ncnn`, not the Electron GUI. Requires Vulkan. |

New picks NOT on the existing ROADMAP, ordered by ROI:

| Tool | URL | Stars | Why wrap it |
|---|---|---:|---|
| **HandBrake CLI** | https://github.com/HandBrake/HandBrake | 23.8k | Canonical video transcoder. Has a fully-supported `HandBrakeCLI` binary, distros already ship it. Best-in-class device presets (Apple/Android/Amazon). **Wrap as the "Device Presets" tab** — frees cli-studio from maintaining its own CRF library. v1.11.2 (Jun 2026), active. |
| **mkvtoolnix (`mkvmerge` / `mkvextract`)** | https://mkvtoolnix.download/ | n/a | De-facto MKV muxer/demuxer. No native TUI. Remux without re-encoding, extract subs, attach fonts, edit chapters. **Wrap for "Video → Tools" tab.** |
| **chafa** | https://github.com/hpjansson/chafa | 5k | Terminal graphics. **Don't just depend on it; surface it as an in-TUI image preview pane** for iTerm2/Kitty/Sixel users. v1.18.2 (Apr 2026). |
| **MLT / `melt`** | https://github.com/mltframework/mlt | 1.8k | Multimedia framework behind Kdenlive. The `melt` CLI is scriptable. Multi-track video editing. v7.40.0 (Jun 2026). Heavy dep but powerful. |
| **ffmpeg-normalize** | PyPI | n/a | Python wrapper for ffmpeg's loudnorm with two-pass analysis. Better than the current single-pass `loudnorm`. |
| **audiowaveform** | https://github.com/bbc/audiowaveform | 2k+ | BBC's tool that generates waveform PNGs from audio. **Wrap to power an audio waveform preview pane** — pairs with chafa. v1.10+. |
| **mupdf / `mutool`** | https://mupdf.com/ | n/a | Render PDFs to images, supports OCR. Alternative to qpdf + tesseract with one dep. |
| **real-esrgan-ncnn** | https://github.com/xinntao/Real-ESRGAN | varies | Direct CLI alternative to upscayl with broader model zoo. |
| **zbarimg** (QR/barcode) | https://github.com/mchehab/zbar | n/a | Quiet CLI win — scan QR/barcodes from images. Drop-in to Image Tools. |
| **`perl-rename` / `rename`** | https://github.com/subogero/rename | n/a | Mass-rename media files based on EXIF. Drop-in next to EXIF stripper. |
| **`ffmpeg` codec presets surface** | already in ffmpeg | n/a | x264 `-preset slow`, x265 `-tune grain`, SVT-AV1 `-preset 4`. cli-studio hardcodes libx264 today — surface a "Codec" submenu. |

### 9.3 Tools to NOT add (deliberate non-goals)

- **ytfzf / yt-x / xytz / Feather** — saturated YouTube TUI niche. Mention in docs as alternatives for the "download from YouTube" flow; let cli-studio own the editing side.
- **UpScayl GUI** (Electron) — wrap the CLI `upscayl-ncnn`, not the GUI.
- **Sox** — dormant since 2015. Use `ffmpeg-normalize` + ffmpeg filters instead.

### 9.4 TUI frameworks to consider only if a rewrite happens

cli-studio should stay on **Textual**. The lazygit pattern (one TUI framework, one binary, two commands to install) is what makes xytz shipable; cli-studio's Python+venv+install-script makes that harder. Possible future direction: a thin Go front-end using Bubble Tea, with a Python subprocess for the actual media work — but that's a v2.0 architectural shift.

| Framework | Stars | Language | When to consider |
|---|---:|---|---|
| **Textual** (current) | 36.6k | Python | Stay here. Best-in-class widget set. Async-native. |
| **Bubble Tea** | 43.8k | Go | Most active TUI ecosystem. Charm ecosystem (Lipgloss, Bubbles). |
| **Ratatui** | 21.7k | Rust | Rust equivalent of Bubble Tea. Used by vic, ffdash, visualvault. |
| **Urwid** | n/a | Python | Mature but Windows-broken. ytcon uses it. Avoid. |

### 9.5 The "lazyffmpeg" gap

The user asked specifically about the `tig`/`lazygit` pattern. There is no "lazygit of ffmpeg" yet — **that is cli-studio's opportunity**. The closest neighbors:

- **xytz** is the "lazyffmpeg for YouTube" (528 stars).
- **cli-studio** is the "lazyffmpeg for everything ffmpeg" (the 37-tool surface is unique).
- **visualvault** is the "lazygit of photo organization" (63 stars).
- **ffdash** is the "lazygit of batch video encoding" (64 stars).

**No single tool spans ffmpeg + yt-dlp + ImageMagick + Pillow + ExifTool + (pandoc, qpdf, tesseract, rclone, gallery-dl, whisper.cpp, upscayl).** cli-studio's moat is breadth.

---

## 10. Final score breakdown

| Dimension | Score | Justification |
|---|---:|---|
| Architecture | 8/10 | Registry pattern, modular split, step-state flow. Clean. |
| Code quality | 5/10 | AI artifacts (patch_system.py), bare excepts, copy-paste CSS, magic constants. |
| Security | 4/10 | Chrome cookie flag hardcoded; markup injection; `curl | bash` install; no atomic config write. |
| UX | 8/10 | Real batch processing, themes work, help modal exists, file picker is great. |
| Documentation | 5/10 | Marketing tone, drift between files, version pinning wrong. |
| Testing | 1/10 | Zero tests. |
| Features (breadth) | 9/10 | 37 tools, 5 backends. Unique in the landscape. |
| Features (depth) | 6/10 | Batch logic inconsistent (some tools batch, some don't), some flows have bugs. |
| Distribution | 5/10 | `curl | bash` anti-pattern; install script uses sudo without password handling. |
| **Composite** | **6.5/10** | Working tool with clear moat; needs cleanup, security hardening, and Tier 1 fixes before next release. |

The June-2026 Code Reality Audit in `AGENTS.md` rates cli-studio 7/10. The project's own README claims "v1.0" implicitly via the polished docs. **6.5/10 is the honest score**: the project works, the architecture is sound, but the artifact evidence and security posture justify dropping half a point.

---

## 11. Suggested file additions (for the cleanup PR)

These are not code changes — these are *files to add* alongside the cleanup commits, not edits to existing source.

- `cli-studio/CRITICAL_ASSESSMENT.md` — this document.
- `cli-studio/.gitignore` — exclude `.venv/`, `__pycache__/`, `pyte_debug.log`, `terminal_error.log`, `.obsidian/`.
- `cli-studio/pyproject.toml` — proper packaging, pinned deps with upper bounds, optional-deps groups.
- `cli-studio/tests/` — even one smoke test (`test_cli_studio_imports.py`) is better than zero.
- `cli-studio/CONTRIBUTING.md` — how to add a tool to the registry.
- `cli-studio/SECURITY.md` — privacy stance on cookie extraction, network calls.

---

## 12. Closing

CLI-Studio is the most concrete of the CodeFXR projects — it has a real, demonstrable user value (one TUI wrapping five powerful CLIs), a clean architecture, and a breadth-of-features moat that no competitor matches. The work to get it to "real v1.0" is not a rewrite. It is:

1. **Tier 1 cleanup** (§8.1) — delete the patch script, fix the broken requirement versions, replace the bare excepts, escape user input in markup, validate ffmpeg inputs. ~1 day of focused work.
2. **Tier 2 refactor** (§8.2) — collapse the CSS duplication, the modal duplication, the workflow boilerplate. ~3 days.
3. **Tier 3 features** (§8.3) — pick 3-5 from the ROADMAP, ship them, update the docs honestly. ~2 weeks.

After that, cli-studio genuinely deserves the "v1.0 Gold Master" treatment and is the strongest candidate to be the **flagship of the CodeFXR suite**. The architecture is already there; the polish isn't.
