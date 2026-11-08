# CLI-Studio — Cleanup Roadmap

> **Purpose.** Active working doc. The single point of reference for what's been done, what's in progress, and what's next. If you're catching up, **start here**.
> **Last updated.** 2026-07-22 (post-Phase-19 cleanup: 74 tools, 151 tests, score 9.3/10)
> **Current phase.** All cleanup work complete; v1.0 release-ready pending user ship call.

---

## Where we are

- [DONE] **Phase 0–4** complete (2026-07-16) — cleanup: security, fixes, hygiene, refactor.
- [DONE] **Phase 5** complete (2026-07-21) — tests + CI: 110 pytest tests, ruff + mypy clean.
- [DONE] **Phase 6** complete (2026-07-21) — all 7 batches shipped: pandoc, tesseract, qpdf, mkvtoolnix, codec presets, ffmpeg-filter wraps (hardsubs, silence removal, audio visualizer), mkv extras (attachments, mux subs), EXIF tools (set tag, copy, rename), sprite sheet, HandBrake device presets (new "Device Presets" tab), HW-accel selection, gallery-dl + ffmpeg-normalize + rclone, mupdf/mutool (3 PDF flows). 70 tools total (was 37; +89%); 110 tests pass.
- [DONE] **Phase 7** complete (2026-07-21) — architectural foundation: pluggable backends, regular-menu settings, and user plugin discovery. 70 tools total; 122 tests pass.
- [DONE] **Post-Phase-7 feature sprint** complete — image and waveform previews, optional Whisper subtitle generation, and Real-ESRGAN upscaling workflows. 74 tools total; 129 tests pass. Public release work remains intentionally deferred.
- [DONE] **Phase 8–17** complete (2026-07-21) — argv-input validators, burn-subtitles filter escape for `[`, `]`, `,`, `;`, exiftool `-overwrite_original` for strip-metadata, dead `Cloud Tools` menu removed, codec-aware extract-subs, theme-aware log colors, file_file_in_out_flow helpers, install-script hardening (RC diff prompt, optional-deps warning). See `CLEANUP_ROADMAP_part2.md` for the full worklog.
- [DONE] **Phase 18 polish** complete (2026-07-21) — trim-batch output collision fix via `unique_path()` helper, `Backend` base class with `__init_subclass__` contract enforcement, `main()` exported for clean entry-point semantics, `ruff format` applied tree-wide, 13 redundant wizard-step docstrings removed, 15 new tests (burn-subtitles-filter-metachar escape, `/themes` slash-command routing, `Backend` contract enforcement). Tests: 144. Ruff + mypy clean.
- [DONE] **Phase 19 cleanup** complete (2026-07-22) — `_LoggingModalScreen` mixin fix for `PillowProgressScreen` (CRITICAL batch-failure regression); theme-aware "Unknown command" toast; `update.sh` hardened against silent optional-dep pip failures; wizard exception mapping (`ValueError`/`FileNotFoundError`/`OSError`/`Exception` → user-friendly toasts); 7 lambda builders replaced with named functions; `ChafaBackend.build_waveform_command` honors `ffmpeg_overwrite` setting; `cli-studio/` (gh-pages inner tree) added to `.gitignore`; single `IMAGE_EXTENSIONS` constant in `workflows/utils.py`; `pip install .` entry points (`cli-studio`, `cso`) via `[project.scripts]` + `cli_studio.py` shim; 8 wizard step docstrings removed; `_startup_warnings_shown` flag + misleading "shown once per session" text removed; dead `return v` removed from `config.validate_cache_dir`; final lazy `natsort` import lifted. 7 new tests, **151 total**. Ruff + mypy clean. See `CLEANUP_ROADMAP_part3.md` for the full worklog and `CRITICAL_ASSESSMENT_part3.md` for the audit that drove it.

---

A working checklist derived from `CRITICAL_ASSESSMENT.md`. Do these in order. Each phase should end with a clean commit before moving to the next.

---

## Phase 0 — Quick Wins (do these first, ~30 min)

These are zero-risk deletions/edits. Get them out of the way.

- [x] **Delete `patch_system.py`** — committed dead code, AI artifact, will corrupt the project if re-run
- [x] **Replace `requirements.txt` with hardcoded package list in `install` + new `update.sh`** — keeps the dep version pins (`textual>=0.85,<2.0`, `textual-image>=0.10,<2.0`, `Pillow>=10.0,<12.0`, `yt-dlp>=2024.1.1`) inside the install script itself. `cli-studio update` upgrades everything in the venv. See `install:21` and `update.sh:19`.
- [x] **Add `.gitignore`** — excludes `.venv/`, `__pycache__/`, `*.log`, `.obsidian/`, IDE files, OS junk
- [x] **Remove committed `.venv/` (56MB), `.obsidian/` (24KB), `__pycache__/`** — all now gitignored

---

## Phase 1 — Security Hardening (must do before any release, ~4 hours)

- [x] **Settings for cookies/remote-components** — added `yt_dlp_cookies` and `yt_dlp_remote_components` keys to `DEFAULT_CONFIG` (default empty = disabled). `DownloadProgressScreen` now takes `cookies=` and `remote_components=` args. `workflows/shared.py:build_download_flow` reads config and passes values. Default OFF preserves privacy.
- [x] **Atomic config write** — added `_load_full_config()` and `_save_config()` in `config.py`. `_save_config` writes to tempfile + `os.replace()`. `_load_theme_from_config` and `_save_theme_to_config` in `cli-studio.py` refactored to use them. Corruption on crash no longer possible.
- [x] **Escape user input in markup** — three sites fixed with `rich.markup.escape()`: `cli-studio.py:454` (Unknown command), `ui/progress.py:178` and `ui/progress.py:234` (Executing log lines).
- [x] **Validate numeric inputs** — added `validate_resolution`, `validate_dimensions`, `validate_coords`, `validate_decimal` in `config.py`. Applied to: video scale (`workflows/video.py:113`), video FPS extraction (`:36`), video fade duration (`:126`), audio volume (`workflows/audio.py:9`), audio fade (`:53`), image resize (`workflows/image.py:23`), image crop (`:39`), image quality (`:144`), background-color fuzz (`:80`), border size (`:160`).

> **Dropped 2026-07-16:** "Replace `curl ... | bash` in README" — website's `cso.codefxr.com/install` serves the same file as `cli-studio/install` from a GitHub repo. No drift risk, single source of truth. Not a security concern.

---

## Phase 2 — Bug Fixes (correctness, ~2 hours)

- [x] **`get_media_duration` precision** — now rounds total seconds instead of `int()` flooring. Also raised timeout from 1s → 10s. (`workflows/utils.py`)
- [x] **`get_media_duration` raises on errors** — `FileNotFoundError` for missing file, `RuntimeError` for timeout/parse failure. Caller (modal) catches and notifies via `app.notify`. No more silent `"00:01:00"` fallback.
- [x] **Skipped — already done.** `convert("RGB")` for non-PNG targets already present in both single-file and batch Pillow paths.
- [x] **Batch error reporting** — `FfmpegProgressScreen` and `PillowProgressScreen` batch paths now capture returncode, log failures to terminal-log, and surface count via `app.notify(severity="warning")`. No more silent failure.
- [x] **PDF empty-folder notify** — `PillowProgressScreen` PDF flow now notifies "No images found in <path>" and dismisses instead of silently returning.
- [x] **Natural sort for PDF assembly** — added `natsort>=8.0,<10.0` to install + update.sh. PDF flow uses `natsorted()`. `1.png, 2.png, 10.png` now in correct order.
- [x] **Playlist URL detection** — `DownloadProgressScreen` checks `list=` or `playlist?` in URL and notifies user to use "Download Playlist" instead. Single-video behavior preserved (still only downloads first video).
- [x] **Batch support for 3 flows** —
  - `extract subtitles`: already supported batch via `FfmpegProgressScreen`.
  - `remove background color`: now uses `_build_magick_cmds` helper that detects folder input and builds cmds list. `GenericCliProgressScreen` accepts cmds list with progress bar and per-file failure tracking.
  - `apply filter`: same as above.
  - Prompt changed from "Select Image File:" to "Select Image File/Folder:" for `apply filter`.

---

## Phase 3 — Code Hygiene (AI smell cleanup, ~3 hours)

- [x] **Bare excepts replaced** — all 5 `except: pass` clauses (1 in `cli-studio.py`, 3 in `ui/progress.py` for `write_log`, 1 in `ui/screens.py`) now use `except Exception: pass`. This excludes `KeyboardInterrupt` and `SystemExit` so Ctrl+C and shutdown work correctly.
- [x] **Section-marker comments removed** — 5 markers deleted from `ui/progress.py`: `# BATCH PROCESSING LOGIC`, `# SINGLE FILE LOGIC` (×2), `# PDF EXPORT LOGIC`, `# BATCH LOGIC`.
- [x] **Pillow imports lifted to module level** — single `from PIL import Image, ImageOps, ImageDraw` at top of `ui/progress.py`. Removed two lazy imports inside `process_image` and `run_pillow` methods.

---

## Phase 4 — Dedup & Refactor (~1 day)

- [x] **`_LoggingModalScreen` mixin** — extracted. `DownloadProgressScreen`, `FfmpegProgressScreen`, `GenericCliProgressScreen` now inherit from it. `PillowProgressScreen` doesn't (no `write_log`). ~12 LOC saved.
- [x] **`_BaseInputModal` base class** — extracted. `TextInputScreen`, `FilePickerScreen`, `OptionSelectScreen` now share `_submit(value)` method via inheritance. `ui/screens.py` shrank 127 → 102 LOC.
- [x] **`view_stack` removed** — was half-implemented and never reached depth > 1 in practice. `Alt+B` now always goes to the parent menu or home. ~12 LOC saved.
- [x] **`/command` dispatch dict** — replaced 21-line `if/elif` chain with a `_COMMANDS` dict + `_enter_menu` helper. ~10 LOC saved.
- [x] **Theme CSS data-driven** — `THEME_PALETTES` dict (8 themes × 9 keys) + `_theme_css(name, palette)` template. Generates **byte-identical CSS** to the original (verified — both 10,465 chars after stripping comment headers). Preserves pre-existing quirks: t-default includes `#status-label` in help-text rule, t-modern uses `panel_border` for focus+bar instead of `accent`. `studio_themes.py` shrank 267 → 188 LOC.
- [x] **`file_in_out_flow` helper** in `workflows/shared.py` — covers "input → [param] → save picker → progress" pattern. Refactored 7 flows: `build_extract_audio_flow`, `build_mute_video_flow`, `build_create_gif_flow`, `build_reverse_video_flow`, `build_extract_subs_flow`, `build_change_volume_flow`, `build_fade_audio_flow`. Complex flows (OptionSelectScreen or 2+ extra steps) left as-is for now.
- [x] **`apply_theme` keeps both App + Screen classes** — verified that Toast (App-scoped widget) requires the theme class on App. Removing from App would break toast styling. Existing behavior preserved.

---

## Phase 5 — Tests + CI (~1 day)

The project has zero tests. This is the single biggest gap. Do this before adding features.

- [x] **Add `tests/` directory** with at least one smoke test (`test_cli_studio_imports.py`) — verifies all modules import cleanly
- [x] **Add `pyproject.toml`** — proper packaging, pinned deps with upper bounds, optional-deps groups (`[ocr]`, `[cloud]`, `[ai]`)
- [x] **Add GitHub Actions workflow** — `ruff check`, `mypy` (loose mode), `pytest`
- [x] **Mock-subprocess tests** for `workflows/*.py` — verify each builder returns the right `FfmpegProgressScreen`/`PillowProgressScreen` with the right args
- [x] **Textual `Pilot` UI tests** for the command dispatch (`/video`, `/themes`, `/exit`)

**Result (2026-07-21):** 39 tests passing. `tests/conftest.py` loads the hyphen-named `cli-studio.py` via `importlib.util.spec_from_file_location`. `tests/test_cli_studio_imports.py` is the smoke test (9 tests covering module imports, registry inventory, theme/help invariants, validator sanity, mixin/base inheritance). `tests/test_workflows.py` walks every wizard pattern (file_in_out_flow with/without param, OptionSelect-driven builders, ImageMagick/Pillow/ExifTool/yt-dlp targets, the full 37-entry COMMAND_REGISTRY). `tests/test_app.py` uses Textual's `run_test()` Pilot to drive slash commands and verify view state changes.

`pyproject.toml` v1.0.0 with optional-deps (`ocr = [pytesseract]`, `cloud = [rclone-python]`, `ai = [faster-whisper]`) and a `dev` extras group (`pytest`, `pytest-asyncio`, `ruff`, `mypy`). `install` and `update.sh` had their `textual` upper bound relaxed from `<2.0` to `<7.0` to keep up with Textual's actual version numbering.

CI matrix: Python 3.10, 3.11, 3.12, 3.13. Ruff and pytest gate; mypy is `continue-on-error: true` (loose mode) so type-hint gaps don't block PRs.

---

## Phase 6 — Feature Additions (in order of ROI, ~2-4 weeks)

Pick 3-5 from this list per release. Don't try to do all of them.

### High ROI, low effort

- [x] **Wrap `pandoc`** — new `workflows/documents.py`, "Documents" tab. Universal use case. *Shipped 2026-07-21.*
- [x] **Wrap `qpdf`** — merge / split / encrypt / decrypt PDFs. *Shipped 2026-07-21.*
- [x] **Wrap `tesseract`** — "Extract Text from Image". Drop-in. *Shipped 2026-07-21.*
- [x] **Wrap `mkvtoolnix`** (`mkvmerge` / `mkvextract`) — remux without re-encoding, extract subs. *Shipped 2026-07-21.*
- [x] **Wrap `HandBrake CLI`** — "Device Presets" tab. Beats maintaining a custom CRF library. *Shipped 2026-07-21.*
- [x] **Surface ffmpeg codec presets** — x264 `-preset`, x265 `-tune`, SVT-AV1. Currently hardcoded libx264. *Shipped 2026-07-21.*
- [x] **Burn subtitles (hardsubs)** — `subtitles=` filter. ROADMAP item already. *Shipped 2026-07-21.*
- [x] **Silence removal** — `silenceremove` filter. ROADMAP item already. *Shipped 2026-07-21.*

### High ROI, medium effort

- [x] **Wrap `chafa` as an in-TUI image preview pane** — `Preview Image` renders ANSI output in a themed preview screen. `chafa` remains a system dependency.
- [x] **Wrap `audiowaveform` + chafa** for audio waveform preview. `audiowaveform` is used when installed; FFmpeg `showwaves` is the fallback.
- [x] **Whisper subtitle generation** — `Generate Whisper Subtitles` supports faster-whisper model, language, SRT/VTT output, optional model cache, device, and compute settings. The `ai` dependency remains optional.
- [x] **Real-ESRGAN image upscaling** — `Upscale Image` builds single-file or folder jobs for the external `realesrgan-ncnn-vulkan` binary and supports model, scale, and tile size choices.
- [x] **HW-accel codec selection** — NVENC / VideoToolbox / VAAPI toggle via `hw_accel` config key. *Shipped 2026-07-21.*
- [x] **EXIF metadata editor (write, not just strip)** — exiftool set tag + tagsFromFile flows. *Shipped 2026-07-21.*
- [x] **Wrap `gallery-dl`** — image galleries from Reddit/Imgur/Pixiv. *Shipped 2026-07-21.*
- [x] **Wrap `ffmpeg-normalize`** — Python wrapper for two-pass loudnorm. Replaces single-pass `-af loudnorm`. *Shipped 2026-07-21.*

### Medium ROI

- [x] **Wrap `rclone`** — cloud upload of finished files. *Shipped 2026-07-21.*
- [x] **Wrap `mupdf` / `mutool`** — alternative to qpdf + tesseract for PDFs. *Shipped 2026-07-21 (3 flows).*
- [x] **Spritesheet/montage** — `magick montage`. *Shipped 2026-07-21.*
- [x] **Audio visualizer** — `showwaves` filter. *Shipped 2026-07-21.*
- [x] **Wrap `zbarimg`** — QR/barcode scanning from images. Quick win. *Shipped 2026-07-21.*
- [x] **Wrap `perl-rename`** — mass-rename media files based on EXIF (via exiftool `-FileName<DateTimeOriginal`). *Shipped 2026-07-21.*

### Deliberate non-goals (don't add)

- YouTube TUI competitors (xytz, ytfzf, yt-x, Feather) — saturated niche, cite them in docs as alternatives instead
- UpScayl GUI (Electron) — wrap the CLI `upscayl-ncnn`, not the GUI
- SoX — dormant since 2015, use ffmpeg filters instead

---

## Phase 7 — Architectural (v2.0 thinking, only after Phase 6 ships)

- [x] **Pluggable backend abstraction** — `workflows/backends/` provides a shared `Backend` base and registered `ImageMagickBackend`, `PillowBackend`, `YtDlpBackend`, and `GalleryDlBackend` implementations. Existing image, yt-dlp, and gallery-dl flows route through the registry without changing their default command arguments.
- [x] **Settings menu** — `/settings` and `Alt+S` open the same regular menu panel used by the other sections. Cookies, remote components, hardware acceleration, FFmpeg overwrite, and Whisper preferences are editable there; theme selection remains exclusively in `/themes`. Values use the existing atomic config writer.
- [x] **Plugin system** — startup loads `~/.cli-studio/plugins/*.py` files exposing `PLUGIN_REGISTRY`, optional `PLUGIN_MENU`, and optional `PLUGIN_HELP`. Built-in commands win collisions; valid plugin commands appear in the Plugins menu.

The Phase 7 architecture now supports the preview, optional AI, and external Vulkan workflows described above. Public release metadata remains intentionally unchanged.

---

## Progress tracking

Suggested commit cadence:

- After Phase 0: `chore: delete patch_system.py, fix requirements, gitignore .venv`
- After Phase 1: `security: cookie/network flags opt-in, atomic config, escape markup`
- After Phase 2: `fix: media-duration precision, batch error reporting, natural sort`
- After Phase 3: `chore: replace bare except, remove AI-style comments, module-level imports`
- After Phase 4: `refactor: shared modal base, theme data-driven, command dispatch table`
- After Phase 5: `test: smoke tests, pyproject.toml, CI`
- After each Phase 6 task: `feat: wrap <tool>` or `feat: <capability>`
- After Phase 7: `feat: add pluggable backends, settings, and plugins`

---

**Total estimate to reach honest v1.0 (Phases 0-5): ~1 week focused work.**
**Total estimate to ship Tier-1 features (Phase 6 first 4 items): ~3-4 weeks.**

The architecture is already there. The work is polish, not rewrite.
