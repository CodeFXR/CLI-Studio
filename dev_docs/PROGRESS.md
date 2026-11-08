# CLI-Studio — Progress & Roadmap

> **Purpose.** Single source of truth for what was done, what's happening now, and what's planned next.
> **Last updated.** 2026-07-22 (post-Phase-19 cleanup: 74 tools, 151 tests, ruff + mypy clean, score 9.3/10)

---

## Current focus

**Phases 0–19 complete.** Cleanup roadmaps from `CRITICAL_ASSESSMENT.md`, `CRITICAL_ASSESSMENT_part2.md`, and `CRITICAL_ASSESSMENT_part3.md` fully executed. Tools: **74**. Tests: **151** (was 144; +7 Phase 19 tests). `ruff check` and `mypy` both pass cleanly.

The dev_docs and user-facing README + website_docs are updated; the public release remains on hold.

---

## Recently completed

- **Phase 19 cleanup pass (2026-07-22).** Audit-driven cleanup from `CRITICAL_ASSESSMENT_part3.md` and `CLEANUP_ROADMAP_part3.md`. Closed out: **CRITICAL bug fix** — `PillowProgressScreen` now inherits `_LoggingModalScreen` so the batch failure path no longer AttributeErrors on a corrupt/permission-denied image; **theme-aware "Unknown command" toast** via `log_palette_colors(self.active_theme)`; **`update.sh` hardened** to warn on optional-dep pip failure (was the only `|| true` left in the install path); **wizard exception mapping** in `_BaseInputModal._submit` (`ValueError` → "Invalid input", `FileNotFoundError` → "File not found: …", `OSError` → "File system error: …", generic `Exception` → "Unexpected error; press '?' for help." — full traceback goes to `logger.exception()`); **7 lambda builders replaced with named `_build_*()` functions** in `COMMAND_REGISTRY` for better stack traces; **`ChafaBackend.build_waveform_command` honors the `ffmpeg_overwrite` setting** (was hardcoded `-y`); **`cli-studio/` (gh-pages inner tree) added to `.gitignore`**; **single `IMAGE_EXTENSIONS` constant** in `workflows/utils.py`; **`pip install .` entry points** (`cli-studio`, `cso`) via `[project.scripts]` + a small `cli_studio.py` shim; **8 wizard step-enumeration docstrings removed** (helper contract docstrings preserved); **`_startup_warnings_shown` flag + misleading "shown once per session" text removed**; **last lazy `from natsort import natsorted` lifted to module top**; **dead duplicate `return v` removed** from `config.validate_cache_dir`. New tests: Pillow `_LoggingModalScreen` inheritance + `_log_msg` rendering, wizard `ValueError`/`FileNotFoundError`/`Exception` mapping (3), chafa waveform respects `ffmpeg_overwrite`, every registered command appears in some menu (orphan guard). 7 new tests, **151 total**. Ruff + mypy clean. Internal docs (`PROGRESS`, `ARCHITECTURE`, `CLEANUP_ROADMAP_part3`, `CRITICAL_ASSESSMENT_part3`, `SECURITY.md`, `README.md`, `website_docs.md`) all updated.

- **Phase 18 polish + ruff format (2026-07-21).** Trim-batch output filename collisions fixed via a new `unique_path()` helper in `workflows/utils.py` (collision-safe counter suffixes, applied to FfmpegProgressScreen and PillowProgressScreen batch modes). `Backend` base class now uses `__init_subclass__` to enforce that every concrete backend declares `name` and `operations`. `cli-studio.py` exports a `main()` function for clean entry-point semantics. `ruff format` applied across the tree (25 files reformatted, 15 unchanged); 144 tests, ruff lint, mypy all green. 13 redundant wizard-step docstrings removed from `workflows/*.py` while keeping WHY-content docstrings. Three new test groups added: burn-subtitles-filter-metachar escaping (`[`, `]`, `,`, `;`, `'`), `/themes <name>` and `/themes <empty>` slash-command routing, and `Backend` contract enforcement. Internal docs (PROGRESS, ARCHITECTURE, CRITICAL_ASSESSMENT_part2) updated to reflect this pass.

- **Phase 8–17 cleanup pass (2026-07-21).** Argv-input validators (`validate_pages`, `validate_remote_name`, `validate_exif_tag`, `validate_cache_dir`) added and wired through mutool / qpdf / rclone / exiftool-set / Whisper cache-dir flows. `burn_subtitles` filter escape extended for `[`, `]`, `,`, `;`. `strip metadata` now passes `-overwrite_original`. Dead `Cloud Tools` menu entry removed. `textual-image` warning shown once per session. `extract subtitles` probes codec and uses the right extension. `rclone listremotes` writes output to a file via a new `_RcloneListRemotesScreen`. `file_file_in_out_flow` and `file_file_progress_flow` helpers added; 5 flows refactored to use them. Three duplicate `_abspath` definitions consolidated into `workflows/utils.py:abspath`. Lazy `natsort` imports lifted to module top. Log lines use the active theme's accent/fail colors (no more hardcoded `#00dadf` / `#f7768e`). `HelpModal` theme class set in `__init__`. Install script `|| true` replaced with a visible warning; RC append now prints the diff and prompts before writing. 9 new tests (validator rejections, codec-aware extract-subs, rclone argv-injection regression, etc.). 23 help entries added. `SECURITY.md` published. Internal docs (ARCHITECTURE, CLEANUP_ROADMAP_part2, CRITICAL_ASSESSMENT_part2) refreshed.

- **Post-Phase-7 feature sprint (2026-07-21).** Added `Preview Image` through chafa, `Preview Audio Waveform` through audiowaveform with an FFmpeg fallback, `Generate Whisper Subtitles` through optional faster-whisper, and `Upscale Image` through the external Real-ESRGAN ncnn Vulkan binary. Added model/device/compute/cache preferences to the regular Settings menu; theme remains owned by `/themes`. Public release work is deferred.

- **Phase 6 batches 5-7 (2026-07-21).** Phase 6 closed out across three batches.

  *Batch 5 (HandBrake device presets)*
  - New `workflows/handbrake.py` with 16 hardcoded preset names (Apple/Android/Chromecast/Fire TV/Roku/Fast/HQ/etc.) plus a "list presets" debug helper.
  - New `MENU_DEVICES` and 5th top-level entry "Device Presets" in `MENU_MAIN`. Wired up `/devices` command, title case, suggester, menu option list, and Pilot UI test.
  - `cli-studio.py` adds `/devices` to `_COMMANDS` + `CommandSuggester.COMMANDS`; the "Device Presets" elif branch in main-menu dispatch.
  - 4 new tests; tests pass at 99/99.

  *Batch 6 (HW-accel selection)*
  - New `hw_accel` key in `DEFAULT_CONFIG` (default empty = software encoders only). Valid values: `nvenc`, `vaapi`, `videotoolbox`, `qsv`.
  - `workflows/video.py` adds `_codec_choices()` (returns extended codec list when `hw_accel` is set) and `_resolve_encoder()` (maps the user-facing label back to the ffmpeg encoder name).
  - When `hw_accel=nvenc` is in config, the "Convert Video (Preset)" wizard's codec list gains `h264_nvenc (NVIDIA NVENC)`; selecting it emits `-c:v h264_nvenc -preset <chosen>` instead of `libx264`.
  - Existing users see no behavioral change (default = empty).
  - 5 new tests; tests pass at 104/104.

  *Batch 7 (mupdf / mutool)*
  - New `workflows/mupdf.py` with 3 flows: `extract pdf text` (`mutool draw -F text`, complements tesseract for documents that already exist as PDFs), `pdf to images` (`mutool convert` to render pages as PNG/JPG/PPM, 144 dpi default), and `merge pdfs (mutool)` (alt to the qpdf merge flow).
  - 5 new tests including a folder-batch merge with natsort; tests pass at 110/110.

  Adjacent fixes shipped across the 7 batches:
  - `install` + `update.sh` + `.github/workflows/ci.yml` apt lines now install: `pandoc`, `tesseract-ocr` (+ `tesseract-ocr-eng`), `qpdf`, `mkvtoolnix`, `zbar-tools`, `rename`, `rclone`, `handbrake-cli`, `mupdf` (+ Fedora/Arch/macOS equivalents). dnf and pacman and brew equivalents updated in parallel.
  - `pyproject.toml` optional-deps renamed: `cloud` is gone; added `normalizers = [ffmpeg-normalize>=1.27]` and `galleries = [gallery-dl>=1.26]`. `install` and `update.sh` now also `pip install` these two on the side (best-effort with `|| true`).
  - 7 small import/lints squashed as discovered (e.g. `rclone.py` had `state` in the wrong position in a `FilePickerScreen` call; several NameError imports surfaced by parametrizing wizard tests).
  - Inventory tests updated to match (expected-tools list now 70+ items; guard counts raised to 70).

  Total growth this session (Phase 6 batches 5-7): **+13 tools**, **+16 tests**. Combined with Phase 6 batches 1-4 (the previous session): **+33 tools** (37 → 70) and **+110 tests** (0 → 110). Ruff + mypy clean throughout.

- **Phase 6 batch 4 (2026-07-21).** Codec presets for video transcode.
  - New flow `convert video preset` in `workflows/video.py`. Wizard: input → format pick → codec pick (`libx264` / `libx265` / `libsvtav1` / `copy`) → preset pick (per-codec options; `copy` skips) → save picker → progress.
  - x264 and x265 use `-c:v libx{264,265} -preset <name>` with presets `ultrafast`/`superfast`/`veryfast`/`faster`/`fast`/`medium`/`slow`/`slower`/`veryslow`.
  - SVT-AV1 uses `-c:v libsvtav1 -preset <int>` with options `0`/`4`/`6`/`8`/`10`/`12` (lower = slower = better; 6 is the library default).
  - `copy` codec emits `-c copy` (no re-encode) and skips the preset step.
  - `config.MENU_VIDEO` grows from 19 → 20 items; +1 in `config.HELP_REGISTRY`; +1 in registry (51 tools).
  - Tests: 4 new — `libx264 + slow`, `libx265 + veryslow`, `libsvtav1 + 10`, `copy skips preset step` (asserts no `preset` key in state). **65 tests passing** (was 61).
  - Did NOT add any system-dep changes (ffmpeg preset support is built in).
  - Did NOT modify the existing `convert video` flow — new flow is named "Convert Video (Preset)" and uses a different registry key `convert video preset`.

- **Phase 6 batch 3 (2026-07-21).** mkvtoolnix wraps for the Video tab.
  - New `workflows/mkv.py` with 3 builders: `build_remux_to_mkv_flow`, `build_merge_mkvs_flow`, `build_extract_mkv_subs_flow`.
  - `remux video to mkv` — `mkvmerge -o out.mkv in.<anything>`, container-only change, no re-encode.
  - `merge mkvs` — folder input is natsorted, files passed to `mkvmerge -o out.mkv a.mkv + b.mkv + c.mkv` with `+` separators for lossless concatenation. Single-file input uses the simpler form (`mkvmerge -o out.mkv in.mkv`).
  - `extract mkv subs` — pre-flights with ffprobe (subprocess.run, 10s timeout, swallows FileNotFound/TimeoutExpired/JSON errors → returns empty list) to enumerate subtitle streams, then runs mkvextract once per track. Files are saved as `<base>_<lang>.srt` (or `<base>_<N>.srt` when no language tag).
  - Added `os.path.abspath` resolution to the merge flow so folder inputs don't break when CWD differs from the selected folder.
  - `config.MENU_VIDEO` grows from 16 → 19 items.
  - 3 new registry entries — **50 tools total** (was 47).
  - `install` adds `mkvtoolnix` to apt/dnf/pacman/brew; CI apt line updated.
  - Tests: 9 new — single-file merge, folder-merge with `+` separator count, mkvextract one-cmd-per-track, no-subs returns None, ffprobe missing → empty list, ffprobe bad JSON → empty list, ffprobe valid JSON → parsed correctly, 2 more for the helper. **61 tests passing** (was 52).

- **Phase 6 batch 2 (2026-07-21).** qpdf wraps for the Documents tab.
  - `workflows/documents.py` gains a small `_qpdf_flow` helper (input → [param] → save → progress) and 4 builders: `merge pdfs`, `split pdf`, `encrypt pdf`, `decrypt pdf`.
  - `merge pdfs` accepts a folder of PDFs (natsort, so `1.pdf, 2.pdf, 10.pdf` order is right) or a single PDF. `qpdf --empty --pages in1.pdf in2.pdf … -- merged.pdf` is the call shape.
  - `split pdf` accepts an optional qpdf-format page range (`1-5, 7, 10-12`); empty = full copy.
  - `encrypt pdf` uses `--encrypt <pw> <pw> 256` (AES-256, same password for user and owner).
  - `decrypt pdf` uses `--decrypt --password=<pw>`.
  - `config.MENU_DOCUMENTS` grows to 9 items; 4 new entries in `config.HELP_REGISTRY`.
  - `workflows/registry.py` adds 4 commands — **47 total** (was 43).
  - `install` adds `qpdf` to apt/dnf/pacman/brew system-dep lists.
  - `.github/workflows/ci.yml` apt install line updated.
  - Tests: 6 new in `test_workflows.py` — single-file merge, folder-iterate merge using `tmp_path`, split-with-range, split-no-range, encrypt-uses-AES256, decrypt-uses-password-flag. **52 tests passing** (was 46).

- **Phase 6 batch 1 (2026-07-21).** First feature adds since cleanup.
  - New `workflows/documents.py` with 5 pandoc flows: `markdown to html`, `html to markdown`, `markdown to docx`, `docx to markdown`, `markdown to pdf`.
  - New `build_extract_text_flow` in `workflows/image.py` — wraps `tesseract` for single-image OCR; language picker (eng/deu/fra/spa/ita); `-l <lang>` plumbed through to the subprocess.
  - `config.MENU_MAIN` gains "Documents Tools"; new `config.MENU_DOCUMENTS` and `config.MENUS["documents"]` entry.
  - `config.MENU_IMAGE` gains "Extract Text from Image".
  - `config.HELP_REGISTRY` gains 6 new entries (tesseract + 5 pandoc flows).
  - `workflows/registry.py` registers 6 new commands — total now **43 tools**.
  - `cli-studio.py` adds `/documents` to `_COMMANDS` and `CommandSuggester.COMMANDS`; adds "Documents Tools" branch to `on_option_list_option_selected`; adds "documents" title to `_populate_menu_list`.
  - `install` adds `pandoc`, `tesseract-ocr` (+ `tesseract-ocr-eng`) to apt, `pandoc` + `tesseract` to brew/dnf/pacman.
  - `.github/workflows/ci.yml` apt installs updated to match.
  - Tests: 7 new tests — tesseract + 5 pandoc flows in `test_workflows.py`, `/documents` Pilot test in `test_app.py`. **46 tests passing** (was 39). Ruff + mypy still clean.
  - First release candidate since the cleanup work. Version: `v1.0.0`.

- **Cleanup, Phase 5 complete (2026-07-21).** Tests + CI.
  - `pyproject.toml` (v1.0.0) with optional-deps (`ocr`, `cloud`, `ai`), `dev` extras, `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]`.
  - `tests/test_cli_studio_imports.py` (9 tests) — module smoke, registry inventory, theme + help invariants, validator sanity, mixin/base-class inheritance.
  - `tests/test_workflows.py` (22 tests) — every wizard pattern (`file_in_out_flow` ± param + validator, `OptionSelect`-driven builders, ImageMagick/Pillow/ExifTool/yt-dlp targets, all 37 `COMMAND_REGISTRY` entries dispatched).
  - `tests/test_app.py` (9 tests) — Textual `Pilot` UI tests for `/video`, `/audio`, `/image`, `/themes`, `/about`, `/exit`, `/home`, unknown-command output, and `apply_theme` class propagation.
  - `.github/workflows/ci.yml` — matrix `[3.10, 3.11, 3.12, 3.13]`, runs `ruff check`, `mypy` (loose, `continue-on-error`), `pytest`.
  - `tests/conftest.py` — loads hyphen-named `cli-studio.py` via `importlib.util` so `CliStudioApp` is available to all tests.
  - Adjacent fix: relaxed `textual` pin from `<2.0` to `<7.0` in both `install` and `update.sh` so the install doesn't force-downgrade to Textual 1.0 on modern systems.
  - Adjacent fix: bumped `CliStudioApp.VERSION` to `v1.0.0` to match `pyproject.toml` and the released repo.
  - Adjacent fix: renamed `l, t, r, b` → `left, top, right, bottom` in `config.py`/`workflows/image.py` to clear E741.
  - Adjacent fix: `stdout=PIPE, stderr=PIPE` → `capture_output=True` in `ui/progress.py:160` to clear UP022.
  - 39 tests passing in ~8s. Ruff and mypy clean.

- **Cleanup, Phase 4 complete (2026-07-16).** Refactor.
  - `_LoggingModalScreen` mixin extracted (3 progress screens now share `write_log`)
  - `_BaseInputModal` base class extracted (3 input modals share `_submit`)
  - Dead `view_stack` removed
  - `/command` if/elif chain replaced with dispatch dict + `_enter_menu` helper
  - Theme CSS data-driven — palette dict + template, **byte-identical CSS output** verified, preserved pre-existing quirks (t-modern focus, t-default status-label)
  - `file_in_out_flow` helper added and used in 7 ffmpeg flows; complex flows left as-is
  - `apply_theme` keeps both App + Screen classes (verified Toast styling requires App scope)
  - CSS byte-identical; no behavior changes for users
- **Cleanup, Phase 3 complete.** Code hygiene.
  - 5 bare `except: pass` clauses replaced with `except Exception: pass` (fixes `KeyboardInterrupt`/`SystemExit` swallowing)
  - 5 section-marker comments removed from `ui/progress.py`
  - 2 lazy Pillow imports lifted to module level
- **Cleanup, Phase 2 complete.** Bug fixes.
  - `get_media_duration` rounds instead of floors, raises on errors (no more silent fallback)
  - Timeout bumped from 1s to 10s for slow disks
  - Batch ffmpeg/Pillow paths now report failures (returncode check + per-file notify)
  - PDF empty-folder no longer hangs silently
  - Natural sort for PDF assembly (`natsort` added as dep)
  - Playlist URL detection with warning in single-video download
  - Batch support added to `remove background color` and `apply filter`
  - `GenericCliProgressScreen` refactored to accept cmds list with progress bar + failure tracking
- **Cleanup, Phase 1 complete.** Security hardening.
  - Atomic config write (tempfile + `os.replace()`)
  - `yt_dlp_cookies` and `yt_dlp_remote_components` moved to config (default OFF)
  - User input escaped in Rich markup at 3 sites
  - Regex validation added for numeric inputs (resolution, dimensions, coords, decimals)
- **Cleanup, Phase 0 complete.**
  - Deleted `patch_system.py` (committed dead-code patch script)
  - Deleted `requirements.txt` (replaced with `PYTHON_PACKAGES` array in `install`)
  - Deleted committed `.venv/`, `.obsidian/`, `__pycache__/`
  - Created `.gitignore` and `update.sh`
  - Modified `install` to bake package list and dispatch `cli-studio update`
  - Updated `README.md` and `website_docs.md`
- **Documentation reorganized.** All internal `.md` files moved to `dev_docs/`. `docs.md` (outdated, redundant) deleted.
- **Code audit completed.** `CRITICAL_ASSESSMENT.md` written. Score: 6.5/10.

---

## Historical progress

### 2026-03 — "Massive Update"
*Pre-cleanup. Captured for historical context.*

- **Visual File Picker (`DirectoryTree`)**: Replaced basic text inputs with a new `FilePickerScreen` that integrates Textual's `DirectoryTree`. Users can now use arrow keys to visually navigate their filesystem to select input files and output destinations.
- **Batch Processing Engine**: If a user selects a *folder* instead of a *file* for an input path, the underlying Worker threads automatically iterate over the directory, processing every matching media file.
- **Convert Images to PDF**: Added a pipeline allowing users to select an entire folder of images and instantly stitch them into a single, multi-page PDF document.
- **Feature Set**: Application now at 37 unique, fully-integrated capabilities.

### Video Tools (FFmpeg & yt-dlp)
- Download Video, Download Playlist, Convert Video, Trim Video, Extract Audio, Mute Video, Change Video Speed, Rotate Video, Reverse Video, Create GIF, Extract Frames, Add Watermark, Add Audio Track, Scale/Resize Video, Fade In Video, Extract Subtitles

### Audio Tools (FFmpeg & yt-dlp)
- Download Audio, Convert Audio, Trim Audio, Change Volume, Change Audio Speed, Reverse Audio, Normalize Audio, Fade In Audio, Mix Audio Tracks

### Image Tools (Pillow, ImageMagick, ExifTool)
- Convert Image, Resize Image, Crop Image, Rotate Image, Flip Image, Remove Background Color, Apply Filter, Strip Metadata, Add Text Watermark, Optimize/Compress, Convert to PDF, Add Border

### Earlier
- Theming engine (8 themes), help system (`?`), log console (`Ctrl+L`), worker threading, command registry, `ffprobe` autofill for trim end-time, anti-flag-injection path handling.

---

## Roadmap

### Near-term (Phase 1, security hardening)

See `CLEANUP_ROADMAP.md` for the full list.

- Move `--cookies-from-browser chrome` and `--remote-components ejs:github` to settings, default off
- Atomic config write (`tempfile` + `os.replace`)
- Escape user input in Rich markup strings
- Validate numeric inputs (resolution, volume, speed) against regex before passing to ffmpeg
- Replace `curl ... | bash` recommendation in README with `git clone && bash install` pattern

### Medium-term (Phases 2-5)

- **Phase 2 — Bug fixes.** Duration truncation, batch error swallowing, PDF natural-sort, `extract subtitles` / `remove background` / `apply filter` batch support, alpha-channel handling in single-file Pillow flow, playlist-URL detection in single-video download.
- **Phase 3 — Code hygiene.** Replace any remaining bare `except:` with specific exceptions, remove section-marker comments, lift lazy Pillow imports to module level.
- **Phase 4 — Refactor.** Modal-screen base class, log mixin, data-driven theme CSS, dispatch dict for `/commands`, `file_in_out_flow` workflow helper, simplify view stack.
- **Phase 5 — Tests + CI.** Smoke tests (`test_cli_studio_imports.py`), `pyproject.toml`, GitHub Actions (ruff + mypy + pytest).

### Long-term (aspirational feature additions)

From the original `ROADMAP.md` (June 2026). Items marked ⭐ are on the high-ROI shortlist; rest are catalogued for awareness.

#### Wraps already on the high-ROI shortlist (Phase 6, post-cleanup)
- ⭐ **Wrap `pandoc`** — new "Documents" tab. Universal use case.
- ⭐ **Wrap `qpdf`** — PDF merge / split / encrypt.
- ⭐ **Wrap `tesseract`** — "Extract Text from Image". Drop-in.
- ⭐ **Wrap `mkvtoolnix` (`mkvmerge` / `mkvextract`)** — remux without re-encoding, extract subs/attachments.
- ⭐ **Wrap `HandBrake CLI`** — "Device Presets" tab. Beats maintaining a custom CRF library.
- ⭐ **Surface ffmpeg codec presets** — x264 `-preset`, x265 `-tune`, SVT-AV1. Currently hardcoded libx264.
- ⭐ **Wrap `chafa` as in-TUI image preview pane** — dramatic UX upgrade for Image Tools.
- ⭐ **HW-accel codec selection** — NVENC / VideoToolbox / VAAPI toggle. (ROADMAP item.)
- ⭐ **EXIF metadata editor (write, not just strip)** — exiftool. (ROADMAP item.)
- ⭐ **Burn subtitles (hardsubs)** — `subtitles=` filter. (ROADMAP item.)

#### Aspirational (Phase 6 backlog)

##### Existing-stack upgrades
- **Green-screen chroma key** — `colorkey` filter. (ROADMAP item.)
- **Picture-in-Picture** — `overlay` filter. (ROADMAP item.)
- **Spritesheet / montage** — `magick montage`. (ROADMAP item.)
- **Silence removal** — `silenceremove` filter. (ROADMAP item.)
- **Audio visualizer generation** — `showwaves` filter. (ROADMAP item.)

##### New wraps
- `gallery-dl` — image galleries from Reddit / Imgur / Pixiv.
- `ffmpeg-normalize` — two-pass loudnorm.
- `audiowaveform` + chafa — audio waveform preview pane.
- `whisper.cpp` or `faster-whisper` — auto-subtitle generation.
- `rclone` — cloud upload of finished files.
- `mupdf` / `mutool` — alternative PDF toolkit.
- `real-esrgan-ncnn` — image upscaling.
- `zbarimg` — QR/barcode scanning.
- `perl-rename` — mass-rename based on EXIF.

### v2.0 (architectural — complete)

- [x] Pluggable backend abstraction (`workflows/backends/` with ImageMagick, Pillow, yt-dlp, and gallery-dl implementations)
- [x] Settings screen (`/settings` and `Alt+S`, persisted through the atomic config writer)
- [x] Plugin system (`~/.cli-studio/plugins/*.py` with `PLUGIN_REGISTRY`, optional menu and help metadata)

---

## Competitive context (for awareness)

CLI-Studio is the only TUI that wraps ffmpeg + yt-dlp + Pillow + ImageMagick + ExifTool in one interface with batch processing. Adjacent tools exist but each covers a narrower slice:

- **xytz** (528*) — best-looking YouTube-only TUI (Go + Bubble Tea). Vim keys, thumbnails.
- **ytfzf** (4.1k*) — de-facto YouTube TUI (POSIX shell + fzf). Stale since 2024.
- **vic** (128*) — Rust + crossterm + chafa. Trim/cut video with frame-accurate markers. **Closest UX competitor.**
- **ffdash** (64*) — Rust + Ratatui. AV1/VP9 batch encoder with HW accel.
- **visualvault** (63*) — Rust + Ratatui. Smart date-based media organizer with EXIF.
- **SubForge** (16*) — Python + Textual + faster-whisper. **Closest Textual sibling project.**

Don't compete on YouTube-TUI; that niche is saturated. The moat is breadth of backends.

---

## Sources / external context

- `dev_docs/ARCHITECTURE.md` — code structure, patterns, conventions, where-not-to-put-things (read this first if you're new).
- `dev_docs/CRITICAL_ASSESSMENT.md` — senior-dev code audit, Part 1 (score 6.5/10, dated 2026-07-15).
- `dev_docs/CRITICAL_ASSESSMENT_part2.md` — senior-dev code audit, Part 2 (score 8.5/10, dated 2026-07-21).
- `dev_docs/CRITICAL_ASSESSMENT_part3.md` — senior-dev code audit, Part 3 (score 9.3/10, dated 2026-07-22).
- `dev_docs/CLEANUP_ROADMAP.md` — Phase 0–4 cleanup checklist (security, bug fixes, refactor).
- `dev_docs/CLEANUP_ROADMAP_part2.md` — Phase 5–18 cleanup checklist (tests, features, polish).
- `dev_docs/CLEANUP_ROADMAP_part3.md` — Phase 19 cleanup checklist (mixin fix, exception mapping, distribution).
- `SECURITY.md` — threat model, what's hardened, what's deferred.
