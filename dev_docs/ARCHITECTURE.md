# CLI-Studio — Architecture Reference

> **Purpose.** Context for LLMs and contributors working on this codebase. Not user-facing.
> **Last updated.** 2026-07-22 (post-Phase-19 cleanup pass)
> **Session state.** Phases 0–19 complete. 74 tools; 151 tests; ruff + mypy clean; score 9.3/10. Public release metadata remains unchanged.

---

## Recent cleanup (Phases 8–17)

See `dev_docs/CLEANUP_ROADMAP_part2.md` for the full Phase 8–17 worklist. Highlights:

- **Phase 8**: 3 markup-injection sites in `cli-studio.py:_update_output` now `escape()` user input.
- **Phase 9**: 4 new argv-input validators (`validate_pages`, `validate_remote_name`, `validate_exif_tag`, `validate_cache_dir`) wired into mutool, qpdf, rclone, exiftool-set, and Whisper cache-dir flows.
- **Phase 10**: `burn subtitles` filter escaping extended for `[`, `]`, `,`, `;`.
- **Phase 11**: `strip metadata` now passes `-overwrite_original` to exiftool (no more `*_original` duplicates).
- **Phase 12**: Removed dead `Cloud Tools` menu item; `textual-image` warning shown once per session; `extract subtitles` now probes codec and uses the right extension; `rclone listremotes` writes to a file via a new `_RcloneListRemotesScreen`.
- **Phase 13**: `file_file_in_out_flow` and `file_file_progress_flow` helpers added; 5 flows (burn subtitles, add watermark, add audio track, mix audio, copy exif) refactored to use them.
- **Phase 14**: 3 duplicate `_abspath` definitions consolidated into `workflows/utils.py:abspath`; lazy `natsort` imports lifted to module top; log lines now use the active theme's accent/fail colors (no more hardcoded `#00dadf`/`#f7768e`); `HelpModal` theme class set in constructor (no first-paint flicker).
- **Phase 15**: Install script `|| true` for optional Python deps replaced with a visible warning; RC append now prints the diff and prompts before writing.
- **Phase 16**: 9 new tests (validator rejections, codec-aware extract-subs, plugin collision sanity, help-coverage completeness, overwrite propagation, dead-menu-item guard).
- **Phase 17**: 23 help entries added for tools that previously fell back to the generic template; `pyproject.toml` description and keywords updated; `SECURITY.md` published.

Test count: 138 (was 129). Ruff and mypy clean.

### Recent cleanup (Phase 19)

See `dev_docs/CLEANUP_ROADMAP_part3.md` for the full Phase 19 worklog. The cleanup
audit (CRITICAL_ASSESSMENT_part3.md) found a regression (PillowProgressScreen was
missing the `_LoggingModalScreen` mixin) and three over-claims. Highlights:

- **Phase 19.A** — Critical fixes:
  - `PillowProgressScreen(_LoggingModalScreen, ModalScreen)` — batch failure path
    no longer AttributeErrors on missing `self.write_log` / `self._log_msg`.
  - `cli-studio.py` "Unknown command" toast uses `log_palette_colors(self.active_theme)`
    for theme-consistent color.
  - `update.sh` now mirrors `install`'s visible-warning pattern for optional-dep
    failures (was the only `|| true` left in the install path).
  - `config.py:validate_cache_dir` dead `return v` removed; final `from natsort
    import natsorted` lazy import lifted to module top.
- **Phase 19.B** — UX polish: wizard step docstrings removed from builders (helpers
  retain their contract docstrings); `_BaseInputModal._submit` maps `ValueError` /
  `FileNotFoundError` / `OSError` / `Exception` to specific toasts (no more raw
  traceback text leaking to users); misleading "shown once per session" text removed.
- **Phase 19.C** — Quality: 7 lambda builders in `COMMAND_REGISTRY` replaced with
  named functions; `ChafaBackend.build_waveform_command` honors the
  `ffmpeg_overwrite` setting (was hardcoded `-y`); `cli-studio/` (gh-pages checkout)
  added to `.gitignore`; single `IMAGE_EXTENSIONS` constant in `workflows/utils.py`.
- **Phase 19.D** — Documentation: `ARCHITECTURE.md` reflects that all four progress
  screens share `_LoggingModalScreen`; new guard test catches orphans
  (commands registered but not in any menu).

Test count: 151 (was 144). Ruff and mypy clean.

---

---

## 1. Project at a glance

CLI-Studio is a Textual TUI that wraps `ffmpeg`, `yt-dlp`, `Pillow`, `ImageMagick`, `ExifTool`, `pandoc`, `tesseract`, `qpdf`, `mkvtoolnix`, `HandBrakeCLI`, `gallery-dl`, `ffmpeg-normalize`, `rclone`, `mutool`, `zbarimg`, chafa, optional faster-whisper, and Real-ESRGAN ncnn behind 74 menu-driven media and document tools across 5 top-level tabs. Linux + macOS. Python 3.10+.

The user is **not** a software engineer by trade. They use Fedora as their daily driver, value terminal-native workflows, and prefer minimal manual maintenance (e.g., the install script owns the Python package list — `pyproject.toml` provides tooling config and optional-deps groups, but the install path uses the bash array).

---

## 2. File structure

```
cli-studio/
├── cli-studio.py              # Entry point. CliStudioApp, navigation state, _COMMANDS dispatch dict. VERSION = "v1.0.0".
├── config.py                  # Static menus, HELP_REGISTRY, get_help(), config load/save, validation helpers
├── studio_themes.py           # LAYOUT_CSS + THEME_PALETTES dict + _theme_css template + THEMES_CSS (data-driven)
├── pyproject.toml             # v1.0.0; pytest + ruff + mypy tooling config; optional-deps groups [ocr, cloud, ai, dev]
├── install                    # Bash installer. PYTHON_PACKAGES array. Creates ~/.local/share/cli-studio + launcher
├── update.sh                  # Bash updater. Triggered by `cli-studio update`. Upgrades venv packages
├── .gitignore                 # Excludes .venv/, __pycache__/, *.log, .obsidian/, IDE files, .pytest_cache/, .ruff_cache/
├── .github/
│   └── workflows/
│       └── ci.yml             # Matrix Python 3.10-3.13. ruff check, mypy (continue-on-error), pytest
├── tests/                     # pytest test suite (151 tests, all passing)
│   ├── conftest.py            # Loads hyphen-named cli-studio.py via importlib; sys.path setup
│   ├── test_cli_studio_imports.py   # Smoke: module imports + registry + theme + help + validator invariants
│   ├── test_workflows.py      # Wizard-stepping tests for every COMMAND_REGISTRY builder
│   ├── test_app.py            # Textual Pilot UI tests for navigation and settings
│   └── test_phase7.py         # Backend, settings, preview, transcription, and plugin tests
├── ui/
│   ├── screens.py             # _BaseInputModal + input screens
│   ├── preview.py             # chafa image/waveform preview modal
│   ├── transcribe.py          # faster-whisper worker modal
│   └── progress.py            # _LoggingModalScreen mixin + DownloadProgressScreen, FfmpegProgressScreen,
│                              #   PillowProgressScreen, GenericCliProgressScreen
├── workflows/
│   ├── backends/              # Phase 7 backend interface, implementations, and registry
│   ├── plugins.py             # Phase 7 user-plugin discovery and registration
│   ├── preview.py             # chafa image/waveform workflow builders
│   ├── transcribe.py          # Whisper subtitle workflow builder
│   ├── esrgan.py              # Real-ESRGAN upscaling workflow builder
│   ├── registry.py            # COMMAND_REGISTRY dict. Maps tool name → builder function
│   ├── shared.py              # Multi-disciplinary flows (download, convert, trim) + file_in_out_flow helper
│   ├── video.py               # FFmpeg video tool builders (15 flows; 5 use file_in_out_flow)
│   ├── audio.py               # FFmpeg audio tool builders (8 flows; 3 use file_in_out_flow)
│   ├── image.py               # Pillow/ImageMagick/tesseract tool builders (13 flows, includes EXIF + zbarimg + sprite)
│   ├── documents.py           # Pandoc + qpdf tool builders (9 flows: md↔html, md↔docx, md→pdf, merge/split/encrypt/decrypt PDFs)
│   ├── mkv.py                 # mkvtoolnix tool builders (5 flows: remux, merge, extract subs, mux subs, extract attachments)
│   ├── handbrake.py           # HandBrake device presets (2 flows: transcode device preset, list presets)
│   ├── cloud.py               # rclone upload flows
│   ├── mupdf.py               # mutool flows (3 flows: extract PDF text, PDF to images, merge PDFs)
│   └── utils.py               # ffprobe wrapper (get_media_duration)
├── dev_docs/                  # Internal docs (this folder). NOT user-facing.
│   ├── ARCHITECTURE.md        # This file
│   ├── PROGRESS.md            # Changelog + roadmap (merged)
│   ├── CRITICAL_ASSESSMENT.md # Senior-dev code audit
│   └── CLEANUP_ROADMAP.md     # Active cleanup checklist
├── README.md                  # GitHub landing. User-uploaded manually, not in version control
└── website_docs.md            # Source for codefxr.com. For LLM to format.
```

---

## 3. Module boundaries

**`cli-studio.py`** is the only file that knows about Textual's app lifecycle. It owns:
- `CliStudioApp` class (Textual App)
- View state: `home`, `about`, `themes`, `menu` (state via `menu_context` only; `view_stack` was removed in Phase 4 as dead code)
- `_COMMANDS` dispatch dict for `/command` parsing (replaced the 21-line `if/elif` chain in Phase 4)
- `_enter_menu(name)` helper for `/video`/`/audio`/`/image` shortcuts
- BINDINGS for global hotkeys
- ASCII art, ABOUT text, config file location
- The `CommandSuggester` for input autocompletion
- The regular-menu settings context and its persisted preferences
- Startup plugin loading into the command registry and menus

It does NOT know how any specific tool works — it delegates to `workflows.registry`.

**`config.py`** holds static data + config I/O + validation:
- `MENU_MAIN`, `MENU_VIDEO`, `MENU_AUDIO`, `MENU_IMAGE`, `MENU_SETTINGS` — lists of strings
- `HELP_REGISTRY` — dict mapping tool name → plain-English description
- `get_help(cmd)` — looks up help, returns fallback if not found
- `DEFAULT_CONFIG` — initial config keys (`default_theme`, `yt_dlp_cookies`, `yt_dlp_remote_components`, `hw_accel`, `ffmpeg_overwrite`, Whisper model/device/compute/cache preferences)
- `CONFIG_FILE` — path to `~/.cli_studio_config.json`
- `_load_full_config()`, `_save_config(config)` — atomic config I/O (Phase 1)
- `validate_resolution`, `validate_dimensions`, `validate_coords`, `validate_decimal` — input validators (Phase 1)

**`studio_themes.py`** is CSS + theme metadata, data-driven as of Phase 4:
- `LAYOUT_CSS` — structural CSS (layout, panels, modals)
- `THEME_PALETTES` — dict of palette dicts (8 themes × 9 keys each: bg, panel, panel_border, logo, version, text, accent, highlight, input_border, status_in_help)
- `_theme_css(name, palette)` — generates per-theme CSS from palette (byte-identical to old hand-written CSS)
- `THEMES_CSS` — generated by joining `_theme_css(name, p)` for all themes
- `THEME_ORDER`, `THEME_NAMES`, `NAME_TO_CLASS` — theme metadata

**`ui/screens.py`** holds the reusable input modals. The Settings view is intentionally part of the app's regular `menu` context rather than a modal:
- `_BaseInputModal(ModalScreen)` — owns `prompt`, `default_val`, `state`, `next_step_func`, `action_cancel()`, `_submit(value)`
- `TextInputScreen(_BaseInputModal)` — adds `placeholder`
- `FilePickerScreen(_BaseInputModal)` — adds DirectoryTree, directory-selected handlers
- `OptionSelectScreen(_BaseInputModal)` — replaces Input with OptionList

**`ui/preview.py`** owns the themed preview modal. It renders chafa's ANSI output and builds audio waveforms with audiowaveform when available, falling back to FFmpeg `showwaves`.

**`ui/transcribe.py`** owns the threaded faster-whisper worker. The optional dependency is imported only when a transcription starts; subtitle files are written through a temporary file and atomically moved into place.

Each modal calls `self._submit(value)` which validates input, calls `next_step_func(val, state)`, dismisses, and pushes the next themed screen.

**`ui/progress.py`** holds worker modals (one per subprocess backend). All four share `_LoggingModalScreen`:
- `_LoggingModalScreen` — provides `write_log(text)` and `_log_msg(kind, body)` methods (the latter renders a theme-coloured markup line via `studio_themes.log_palette_colors`)
- `DownloadProgressScreen(_LoggingModalScreen, ModalScreen)` — yt-dlp wrapper
- `FfmpegProgressScreen(_LoggingModalScreen, ModalScreen)` — ffmpeg wrapper with batch support
- `GenericCliProgressScreen(_LoggingModalScreen, ModalScreen)` — accepts single cmd or list of cmds
- `PillowProgressScreen(_LoggingModalScreen, ModalScreen)` — Pillow wrapper (uses the mixin for batch failure logging; pre-Phase 19 this was `ModalScreen` only, which broke the batch error path with AttributeError)

Each:
- Runs `self.run_worker(self._run, exclusive=True, thread=True)` on mount
- Streams subprocess stdout to `#terminal-log` via `self.app.call_from_thread(self.write_log, line)`
- Has `action_cancel_*` bound to `escape` that calls `self.process.terminate()`

**`workflows/registry.py`** is the command dispatch:
- `COMMAND_REGISTRY` — `dict[str, callable]` mapping tool name → builder function
- `CommandHandler.handle_command(text)` — looks up, calls builder, returns next modal/screen

**`workflows/backends/`** is the registered backend layer:
- `Backend` — shared name and capability contract
- `BackendRegistry` — named backend lookup and replacement
- `ImageMagickBackend`, `PillowBackend`, `YtDlpBackend`, `GalleryDlBackend` — existing-flow implementations
- `ChafaBackend`, `WhisperBackend`, `EsrganBackend` — preview, optional AI, and external Vulkan implementations

**`workflows/plugins.py`** loads user modules from `~/.cli-studio/plugins/`. A module exposes `PLUGIN_REGISTRY` and may provide `PLUGIN_MENU` and `PLUGIN_HELP`. Built-in registry entries are never overwritten.

**`workflows/shared.py`** holds:
- `build_download_flow(is_audio, is_playlist)` — for YouTube download
- `build_convert_media_flow(is_audio)` — for format conversion
- `build_trim_media_flow(is_video)` — for trim/cut
- `file_in_out_flow(...)` — Phase 4 helper for the "input → optional param → save picker → progress" pattern. Used by 7 ffmpeg flows. Image/Pillow flows don't fit because their progress screen constructor has a different signature; future work could extend with a `make_progress` callable.

**`workflows/*.py`** (video/audio/image) define tool builders. Each `build_X_flow()` returns the **first** modal screen (typically `FilePickerScreen` for input selection). The builder chains `step2`, `step3`, ... closures that thread state and return the next modal.

---

## 4. Key design patterns

### 4.1 Wizard pattern (state + step functions)

Every tool is a wizard:
```python
def build_trim_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Start Time:", "00:00:00", state, step3)
    def step3(start, state):
        state['start'] = start
        return TextInputScreen("End Time:", "00:01:00", state, step4)
    ...
    return FilePickerScreen("Select media:", "", {}, step2)
```

The `state` dict is mutated in-place and threaded through every step. When the final step returns a `*ProgressScreen`, the worker takes over and the wizard is done.

**To add a new tool:** create `build_X_flow()` in the appropriate `workflows/*.py` file, register it in `COMMAND_REGISTRY`, add the menu entry in `config.py`, and add a help entry in `HELP_REGISTRY`.

### 4.2 file_in_out_flow helper (Phase 4)

The common "input → optional TextInput param → save picker → progress" pattern is captured by:
```python
def build_mute_video_flow():
    return file_in_out_flow(
        input_prompt="Select Video File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_muted{ext}",
        action_args=["-c:v", "copy", "-an"],
    )
```

With a TextInput step:
```python
def build_change_volume_flow():
    return file_in_out_flow(
        input_prompt="Select Audio File/Folder:",
        save_prompt="Save As (or batch dir):",
        save_suffix="_vol{ext}",
        action_args=lambda s: ["-filter:a", f"volume={s['vol']}"],
        param_prompt="Volume Multiplier:",
        param_default="2.0",
        param_key="vol",
        param_validator=validate_decimal,
    )
```

Use for new ffmpeg flows. Skip for Pillow/GenericCli flows (signature mismatch).

### 4.3 Command registry dispatch

User selects a menu item → `on_option_list_option_selected` fires → if context != "main", call `CommandHandler.handle_command(selected)` → builder returns first modal → `push_themed_screen()`.

### 4.4 `/command` dispatch (Phase 4)

`/home`, `/back`, `/about`, `/menu`, `/themes`, `/settings`, `/exit`, `/video`, `/audio`, `/image`, `/documents`, and `/devices` are mapped in the `_COMMANDS` dict. Adding a new navigation command: add one line to the dict.

### 4.5 Modal flow + theme propagation

When pushing a modal screen, the app calls `screen.add_class(self.active_theme)` so theme CSS applies. This is in `push_themed_screen()` on `CliStudioApp`.

### 4.6 Worker threading

Heavy subprocess work runs in Textual's threaded worker (`run_worker(thread=True)`). The worker:
1. Spawns subprocess with `subprocess.Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True, bufsize=1)`
2. Reads stdout line-by-line
3. Calls `self.app.call_from_thread(self.write_log, line)` for each line
4. Calls `self.app.call_from_thread(self.dismiss)` when done

Cancellation: `worker.is_cancelled` checked per iteration; on cancel, `self.process.terminate()` is called.

### 4.7 The "pass user path through `abspath(expanduser(p))`" rule

Per AGENTS.md's anti-flag-injection concern: every user-provided path is wrapped before being passed to subprocess. This is the project's security stance.

### 4.8 Atomic config writes (Phase 1)

`_save_config` writes to `tempfile.mkstemp()` then `os.replace()`. Either old or new survives; never a half-written file.

### 4.9 Backend lookup (Phase 7)

Workflow code asks `workflows.backends.get_backend(name)` for a concrete implementation. The default registry preserves existing argv shapes, while `register_backend()` permits an application or plugin to replace an implementation.

### 4.10 Plugin contract (Phase 7)

A plugin file defines a `PLUGIN_REGISTRY` dictionary whose keys are user-facing tool names and whose values are zero-argument wizard builders. `PLUGIN_MENU` selects `plugins` by default or an existing menu context; `PLUGIN_HELP` supplies optional help text. Invalid or failing plugin files are skipped without stopping startup.

---

## 5. CSS / theme preferences

**Layout principles (per `studio_themes.py` `LAYOUT_CSS`):**
- `Screen { layout: vertical; align: center middle; background: transparent; }`
- `Container, Static { background: transparent; border: none; }` by default
- Panels (`#about-panel`, `#menu-panel`, `#themes-panel`) toggle via `display: none/block` controlled by Screen classes (`Screen.themes-open`, `Screen.about-open`, `Screen.menu-open`)
- Settings uses the regular `#menu-panel` and `menu_context="settings"`; it is not a modal and does not duplicate theme selection
- Preview and transcription operations use themed modals (`#preview-dialog` and `#progress-dialog`)
- General input modals are `width: 60; padding: 1 2;`

**Theme structure (per `THEMES_CSS`):**
- Each theme is a class on `Screen` AND on each modal (`.t-default #input-dialog`, etc.)
- Color palette per theme: bg, panel bg, panel border, logo, accent, text
- Bar/ProgressBar uses theme accent
- Toast inherits theme palette

**Theme metadata (`THEME_ORDER`, `THEME_NAMES`, `NAME_TO_CLASS`):**
- `THEME_ORDER` — list of class keys (display order)
- `THEME_NAMES` — `dict[key, display_name]`
- `NAME_TO_CLASS` — reversed `dict[display_name, key]`

Theme command flow: `/themes <name>` → `_apply_theme_by_name(name)` resolves to class key → `apply_theme(key, save_default=False)` removes old class from `self` AND `self.screen`, adds new class, refreshes, prompts to save as default.

**Theme naming inconsistency to know about:**
- `t-default` → "original" (Tokyo Night-ish, cyan accent)
- `t-modern` → "modern" (teal/orange)
- `t-too-modern` → "too modern"
- `t-coppice` → "coppice"
- `t-hunter` → "hunter"
- `t-accident` → "navy" (key "accident", display "navy")
- `t-bleu-gris` → "gris"
- `t-pink` → "pink"

The key/display mismatch (`t-accident` → "navy") is intentional but confusing. Treat the display name as canonical for user-facing strings.

---

## 6. Conventions

### 6.1 Code style
- Type hints encouraged (Python 3.10+ supports `list[str]`, `dict[str, Any]`, `str | None`)
- No comments unless explicitly requested (per AGENTS.md)
- Bare `except: pass` is forbidden — replace with specific exception types
- Module-level Pillow imports (don't import inside methods)
- 4-space indentation, ~100 char line limit

### 6.2 Naming
- Classes: `PascalCase` (`DownloadProgressScreen`)
- Functions/methods: `snake_case` (`build_trim_flow`)
- Constants: `UPPER_SNAKE_CASE` (`PYTHON_PACKAGES`)
- CSS IDs: `kebab-case` (`#input-dialog`, `#menu-list`)
- CSS classes: `kebab-case` (`.t-default`, `.confirm-option`)

### 6.3 Subprocess rules
- Always `subprocess.Popen(cmd, ...)` with **list args, never `shell=True`**
- Always `stdout=PIPE, stderr=STDOUT, text=True, bufsize=1` for streaming
- Always wrap user paths in `os.path.abspath(os.path.expanduser(path))`
- Never pass user input through f-string interpolation into a shell command

### 6.4 File operations
- `os.makedirs(path, exist_ok=True)` for batch output dirs
- Atomic config writes (tempfile + `os.replace()`) — implemented Phase 1, see `config.py:_save_config`
- No committed `.venv/`, no committed logs
- No committed test caches (`.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` are gitignored)

### 6.5 No emojis, no marketing tone in code or comments
- `cli-studio.py`, `config.py`, `studio_themes.py` etc. should be functional, not promotional
- The README has marketing language (acceptable — that's user-facing)
- Internal docs (`dev_docs/`) should be terse and honest

---

## 7. Where NOT to put things

- **Don't put business logic in `cli-studio.py`.** That's the app shell only. New tools go in `workflows/`.
- **Don't add a `requirements.txt`.** The package list lives in `install` (bash array) and `update.sh`. Touch it once a year when a major upstream version lands.
- **Don't import third-party libs inside functions.** Add to imports at the top of the file.
- **Don't use `shell=True` anywhere.** List args to subprocess always.
- **Don't add `fix_*.py` or `patch_*.py` scripts to the repo.** They're one-shot artifacts (lesson learned from the deleted `patch_system.py`).
- **Don't commit `.venv/`, `__pycache__/`, logs, or IDE configs.** All gitignored.

---

## 8. Recent decisions and rationale

| Decision | Why | Date |
|---|---|---|
| Deleted `patch_system.py` | One-shot AI patch script committed in error. Would corrupt the project if re-run. | 2026-07-16 |
| Deleted `requirements.txt` | Replaced with `PYTHON_PACKAGES` bash array in `install` and `update.sh`. Eliminates the manually-maintained file. | 2026-07-16 |
| Added `cli-studio update` command | Launcher dispatches `update` arg to `update.sh`. No in-app update logic. | 2026-07-16 |
| Added `internal/` → renamed to `dev_docs/` folder | Keeps internal docs out of public view; clear that they're not user-facing. | 2026-07-16 |
| Merged `PROGRESS.md` + `ROADMAP.md` | Single source of truth for progression + plans. | 2026-07-16 |
| Pinned `textual>=0.85,<2.0` etc. | Upper bounds protect against breaking changes; lower bounds keep us off ancient versions. | 2026-07-16 |
| Deleted `.obsidian/`, `.venv/`, `__pycache__/` from tree | All gitignored; committing them was a violation of the project's distribution rule. | 2026-07-16 |
| Atomic config write (`_save_config`) | Tempfile + `os.replace()` prevents config corruption on crash. | 2026-07-16 (Phase 1) |
| Settings for cookies/remote-components | Default OFF; previously hardcoded `--cookies-from-browser chrome --remote-components ejs:github`. Privacy-invasive; now opt-in. | 2026-07-16 (Phase 1) |
| User input escaped in Rich markup | Use `rich.markup.escape()` at 3 sites to prevent markup injection. | 2026-07-16 (Phase 1) |
| Regex validation for numeric inputs | `validate_resolution`, `validate_dimensions`, `validate_coords`, `validate_decimal`. | 2026-07-16 (Phase 1) |
| Fixed duration precision | `round()` instead of `int()` floor in `get_media_duration`. | 2026-07-16 (Phase 2) |
| Batch error reporting | FFmpeg/Pillow batch paths now check returncode, log failures, count notify. | 2026-07-16 (Phase 2) |
| Natural sort for PDF | Added `natsort>=8.0,<10.0`. | 2026-07-16 (Phase 2) |
| `_LoggingModalScreen` mixin | Extracted `write_log`. | 2026-07-16 (Phase 4) |
| `_BaseInputModal` base class | Extracted shared submit logic for 3 input modals. | 2026-07-16 (Phase 4) |
| Removed `view_stack` | Dead code; never reached depth > 1. | 2026-07-16 (Phase 4) |
| `/command` dispatch dict | Replaced 21-line if/elif with `_COMMANDS` + `_enter_menu` helper. | 2026-07-16 (Phase 4) |
| Theme CSS data-driven | `THEME_PALETTES` dict + `_theme_css()` template. **Byte-identical** output to old hand-written CSS. | 2026-07-16 (Phase 4) |
| `file_in_out_flow` helper | Used by 7 ffmpeg workflows; complex flows left as-is. | 2026-07-16 (Phase 4) |
| `apply_theme` keeps both App + Screen | Toast styling requires App-scope class; verified, no change. | 2026-07-16 (Phase 4) |

---

## 9. Active cleanup work

**Status (2026-07-21):** Phases 0–17 and the Phase 18 polish pass are complete. The regular settings menu, backend registry, plugin loading, previews, Whisper workflow, Real-ESRGAN workflow, argv-input validators, codec-aware extract-subs, theme-aware log colors, trim-batch collision handling, and `Backend` contract enforcement are all covered by the source tree and tests. See `dev_docs/CLEANUP_ROADMAP_part2.md` for the full Phase 8–17 worklist and `dev_docs/CRITICAL_ASSESSMENT_part2.md` for the audit that motivated it.

---

## 10. Known code smells (do not perpetuate)

These patterns **have been fixed** in Phases 0–5 (do not reintroduce them):

- [DONE] **`write_log(self, text)` method duplicated** in 3 progress screens → extracted to `_LoggingModalScreen` mixin
- [DONE] **Theme CSS hand-copied** 8× → converted to `THEME_PALETTES` dict + template (byte-identical output)
- [DONE] **Modal screens share near-identical submit handlers** → extracted to `_BaseInputModal` base class
- [DONE] **`/command` parsing as 21-line if/elif chain** → replaced with `_COMMANDS` dispatch dict
- [DONE] **Workflows repeat "input → save picker → progress"** → extracted to `file_in_out_flow` helper (used by 7 ffmpeg flows)
- [DONE] **Bare `except: pass`** in 6 places → all replaced with `except Exception: pass` (fixes `KeyboardInterrupt`/`SystemExit` swallowing)
- [DONE] **`view_stack` half-implemented** → removed (dead code)
- [DONE] **`apply_theme` mutates both App and Screen** → verified this is **necessary** (Toast styling requires App-scope class); kept as-is, not a smell
- [DONE] **Section-marker comments** (`# BATCH LOGIC`, `# SINGLE FILE LOGIC`, etc.) → removed
- [DONE] **`l, t, r, b` ambiguous variable names** in crop coords → renamed `left, top, right, bottom` in `config.py` and `workflows/image.py` (Phase 5 follow-up)
- [DONE] **`subprocess.run(..., stdout=PIPE, stderr=PIPE)` in batched ffmpeg** → `capture_output=True` (Phase 5 follow-up, UP022)
- [WARN] **`f"[bold #00dadf]Executing:[/bold #00dadf] {' '.join(cmd)}"`** hardcodes a theme-specific color in 2 places (`ui/progress.py:194, 269`). User input is `escape()`-wrapped (prevents markup injection), but the literal `#00dadf` color is still hardcoded. **Open**: should derive from active theme. Low priority — only visible when log console is open with a non-default theme.

---

## 12. Phase 6 additions (2026-07-21)

**`pandoc` (Documents tab) — 5 flows:** `workflows/documents.py` is a new module. The Wizard shape is `input → save picker → GenericCliProgressScreen` since pandoc's auto-format detection means the input/output extensions alone determine the conversion. Standalone (`-s`) flag is on by default for HTML/PDF targets; off for markdown round-trips.

**`tesseract` (Image Tools) — 1 flow:** `build_extract_text_flow` in `workflows/image.py`. Single-image OCR with a language picker (eng/deu/fra/spa/ita). Calls `tesseract <in> <out_base> -l <lang>` which appends `.txt` to the output path.

**Wiring changes (cli-studio.py):** `_COMMANDS` adds `/documents`; `CommandSuggester.COMMANDS` adds `/documents`; `on_option_list_option_selected` adds the "Documents Tools" branch; `_populate_menu_list` adds the "documents" title case.

**No refactor of `file_in_out_flow` was needed** because pandoc/tesseract don't fit the Ffmpeg-style `(input, output, action_args, target_ext)` kwarg shape — pandoc/tesseract want `(cmds, tool_name, target)` for `GenericCliProgressScreen`. Five new inline-closure builders were simpler than generalising the helper.

**Total tools: 43** (was 37). Tests: 46 (was 39).

---

## 13. Phase 6 batch 2 (2026-07-21): qpdf

Four PDF flows added to the Documents tab using the same `GenericCliProgressScreen` pattern as the pandoc wraps:

- **Merge PDFs** — folder input (or single PDF), natsort, `qpdf --empty --pages in1.pdf in2.pdf … -- merged.pdf`.
- **Split PDF** — page-range input (qpdf format: `1-5, 7, 10-12`); empty = full copy.
- **Encrypt PDF** — `qpdf --encrypt <pw> <pw> 256 -- in.pdf out.pdf` (AES-256, same password for user/owner).
- **Decrypt PDF** — `qpdf --decrypt --password=<pw> in.pdf out.pdf`.

The four builders share a small `_qpdf_flow` helper in `workflows/documents.py` — same shape as `file_in_out_flow` but using `GenericCliProgressScreen` instead of `FfmpegProgressScreen`. This is the second use of the wizard pattern, so the helper was worth extracting here even though it didn't fit `file_in_out_flow`'s Ffmpeg-arg shape.

**Total tools: 47** (was 43). Tests: 52 (was 46).

---

## 14. Phase 6 batch 3 (2026-07-21): mkvtoolnix

Three flows added to the Video tab in a new `workflows/mkv.py`:

- **Remux Video to MKV** — `mkvmerge -o out.mkv in.<anything>`. Container-only change, no re-encoding. Useful for MP4/MKV/AVI/etc. → MKV for compatibility with modern players.
- **Merge MKVs** — folder (natsorted) or single MKV. For 2+ files, mkvmerge syntax is `mkvmerge -o out.mkv a.mkv + b.mkv + c.mkv` where `+` is the lossless concatenation separator. Single-file falls through to the simpler `mkvmerge -o out.mkv in.mkv`.
- **Extract MKV Subs** — runs `_probe_subtitle_tracks` (a small ffprobe wrapper inside `workflows/mkv.py` that survives FileNotFoundError, TimeoutExpired, and JSONDecodeError) to enumerate subtitle streams, then constructs one `mkvextract tracks <id>:<out>` command per track. Files are saved as `<base>_<lang>.srt` when a language tag is present, `<base>_<N>.srt` otherwise. Multiple subs = batch mode in `GenericCliProgressScreen`.

**Why a new module (`mkv.py`) instead of `video.py`?** mkvtoolnix is a distinct backend with its own conventions (positional args, `+` separator, ffprobe-pre-flight). Keeping it in its own module is cleaner than bloating `video.py` (~140 LOC of wizard builders in there already).

**Tool-count growth**: 37 → 50 (+35%) in a single cleanup + Phase-6 session.

**Tests**: 9 new (61 total). The extract-MKV-subs tests monkey-patch `_probe_subtitle_tracks` rather than relying on real ffprobe output, which makes them deterministic and fast (~9s total test runtime).

---

## 15. Phase 6 final sprint (2026-07-21): batches 5-7

Three batches to close out the remaining Phase 6 Tier-1 picks (after the previous session's batches 1-4 finished pandoc/tesseract/qpdf/mkvtoolnix/codec-presets):

### 15.1 Batch 5 — HandBrake device presets

`workflows/handbrake.py` (new module) ships 2 flows: `transcode device preset` (pick from 16 hardcoded preset names covering Apple/Android/Chromecast/Fire TV/Roku/Fast/HQ/etc., invoke `HandBrakeCLI -i in -o out --preset <chosen>`) and `list handbrake presets` (run `HandBrakeCLI --preset-list` to dump the full system list to a .txt file for diagnostics).

New top-level tab: `MENU_MAIN` gains "Device Presets"; `MENU_DEVICES = ["Transcode Device Preset", "List HandBrake Presets"]`. `cli-studio.py` adds `/devices` to `_COMMANDS` and `CommandSuggester.COMMANDS`, the "Device Presets" elif branch in `on_option_list_option_selected`, and a `devices` title case in `_populate_menu_list`.

### 15.2 Batch 6 — HW-accel selection (settings-driven)

Adds a `hw_accel` key to `config.DEFAULT_CONFIG` (default empty = software encoders only). Valid values: `nvenc`, `vaapi`, `videotoolbox`, `qsv`. When set, the existing "Convert Video (Preset)" wizard expands the codec list with a hardware variant (e.g. `nvenc` adds `h264_nvenc (NVIDIA NVENC)` to the choice set, which then emits `-c:v h264_nvenc -preset <chosen>`).

Implemented via two small helpers in `workflows/video.py`: `_codec_choices()` (returns the runtime-extended choice list) and `_resolve_encoder(choice)` (maps the user-facing label back to the ffmpeg encoder name). Existing users see no behavioral change.

### 15.3 Batch 7 — mupdf/mutool

`workflows/mupdf.py` (new module) ships 3 flows that complement the qpdf suite without duplicating it:

- `extract pdf text` — `mutool draw -F text` to dump text content from a PDF page range to .txt. Complements tesseract for documents you already have as PDFs (rather than as scanned images).
- `pdf to images` — `mutool convert -O resolution=144` to render pages as PNG/JPG/PPM in a chosen output directory.
- `merge pdfs (mutool)` — `mutool merge -o out file1.pdf file2.pdf …` as an alternative to the qpdf merge flow.

All three live on the Documents tab. Names like `merge pdfs (mutool)` and `merge pdfs` (qpdf) are intentionally distinct so users can pick the backend they prefer.

### 15.4 Final Phase-6 totals

| | Start | Phase 5 | Phase 6 batches 1-4 (prev session) | Phase 6 batches 5-7 (this session) | **Total** |
|---|---:|---:|---:|---:|---:|
| Tools | 37 | 37 | 51 | 70 | **+89%** |
| Tests | 0 | 39 | 65 | 110 | **+110** |
| Backends (CLI-wraps) | 5 | 5 | 9 | 14 | **+9** |

### 15.5 Post-Phase-7 feature sprint

- **Whisper subtitles** — optional faster-whisper worker with model, language, device, compute, cache, SRT, and VTT support.
- **Real-ESRGAN upscaling** — external `realesrgan-ncnn-vulkan` command builder with model, scale, tile, and folder-batch choices.
- **Chafa image preview** — ANSI preview modal using the system `chafa` command.
- **Audio waveform preview** — audiowaveform when installed, with FFmpeg `showwaves` fallback, rendered through chafa.

These features remain optional at runtime: the core app starts without faster-whisper, audiowaveform, or the Real-ESRGAN binary installed.

---

## 11. Glossary

- **Tool** — a single user-facing capability (e.g., "Convert Video"). One entry in `MENU_*` and `COMMAND_REGISTRY`.
- **Flow / builder** — a function `build_X_flow()` that returns the first modal in a wizard.
- **Wizard** — the chained modals (`step2`, `step3`, ...) that gather user input before launching a worker.
- **Worker / progress screen** — a `ModalScreen` that runs a subprocess and shows progress. Takes over after the wizard.
- **State** — the `dict` threaded through wizard steps. Lives in memory only; never persisted.
- **Backend** — a registered implementation in `workflows/backends/` (for example Pillow or ImageMagick) that owns a task's image operation or command construction; separate from the wrapped CLI tool itself.
