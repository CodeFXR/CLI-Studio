# CLI-Studio Agent Guide & Security Audit (CLI_STUDIO_AGENT.md)

## 1. Executive Summary

CLI-Studio is a comprehensive terminal media dashboard and workflow engine (~19,000 lines of Python) built on Textual. It wraps external command-line utilities including FFmpeg, ImageMagick, ExifTool, yt-dlp, gallery-dl, HandBrakeCLI, and Whisper into an interactive TUI.

In November 2026, following user direction, the entire Document Tools section (12 commands wrapping QPDF, Pandoc, and MuPDF) was removed to refocus CLI-Studio strictly on Audio, Video, Image media processing, and Cloud storage. In parallel, critical security vulnerabilities and logic bugs were remediated.

A secondary adversarial multi-model consensus audit was conducted across four LLM reasoning engines (Antigravity, OpenAI Codex, GitHub Copilot CLI, and OpenCode) spawned directly in Herdr (`hc`). While significant improvements in security, type checking, and operational stability were recognized, release packaging gaps and filter edge cases were uncovered, establishing a post-fix consensus score of **6.5 / 10** (up from 4.4 / 10).

---

## 2. Multi-Model Consensus Audit & Scorecard

### Post-Remediation Assessment (Current)

| Evaluator | Engine / Model | Post-Fix Score | Pre-Fix Score | Key Assessment & Verdict |
|---|---|---|---|---|
| **GitHub Copilot CLI** | GPT-6 Luna (Copilot Fusion) | **8.0 / 10** | 4.0 / 10 | Static security review clean; no actionable vulnerabilities in reviewed core; list-argv subprocess execution verified. |
| **Antigravity** (Lead) | Advanced Agentic Lead | **7.0 / 10** | 4.5 / 10 | Critical traversals, data loss, and screen stack corruptions resolved; mypy 0 errors; pytest 134/134 passed; packaging shim needs fix. |
| **OpenCode** | GLM-5.3-Flash | **6.0 / 10** | 5.0 / 10 | Rigorous runtime test: verified MKV sanitization and atomic config; reproduced pip wheel failure for console script and apostrophe bug in hardsub filter. |
| **OpenAI Codex** | GPT-6 Luna (xhigh reasoning) | **5.0 / 10** | 4.0 / 10 | Identified broken pip entry point as release blocker; flagged Rich log display markup escaping and path expansion before isdir. |
| **Consensus Score** | **Multi-LLM Consensus** | **6.5 / 10** | **4.4 / 10** | **Substantial security and stability elevation (+2.1 pts). Core media workflows hardened; packaging and filter edge cases remaining.** |

---

## 3. Remediated Vulnerabilities & Bug Fixes

The following issues identified during the initial audit have been fully remediated and verified:

1. **Arbitrary File Overwrite via MKV Path Traversal (`workflows/mkv.py`)**:
   - Enforced `os.path.basename()` and strict regex filtering (`[A-Za-z0-9_.-]+`) on attachment filenames and subtitle language tags.
   - Added `os.path.commonpath([expanded_out_dir, out_file]) == expanded_out_dir` directory confinement checks.
2. **QPDF Plaintext Passwords in Process Arguments**:
   - Completely resolved by excising the document tools suite (`workflows/documents.py`, `workflows/mupdf.py`). All 12 PDF/Pandoc workflows and passwords in `argv` eliminated.
3. **In-Place Data Loss in "Rename by EXIF Date" (`workflows/image.py`)**:
   - Removed destructive `-overwrite_original` flag.
   - Directed ExifTool output copies to the target directory (`-o {expanded_out}/`), keeping source media untouched.
4. **Startup Arbitrary Code Execution via Unauthenticated Plugins (`workflows/plugins.py`)**:
   - Gated plugin loader behind explicit `"enable_plugins": True` configuration in `config.py` (defaults to `False`).
   - Wired missing Plugins menu navigation in `cli-studio.py`.
5. **Ghost File Outputs in Barcode & Handbrake Presets (`workflows/image.py`, `workflows/handbrake.py`, `ui/progress.py`)**:
   - Implemented stdout redirection and capture in `GenericCliProgressScreen` to write output directly to the chosen `.txt` file.
6. **Worker Cancel Double-Dismiss & Screen Stack Corruption (`ui/progress.py`, `ui/transcribe.py`)**:
   - Created `safe_dismiss()` helper tracking `_dismissed` and `_cancelled` flags across all modal progress screens, preventing secondary calls from popping underlying parent screens.
7. **Pillow Batch Image Memory and File Descriptor Leak (`ui/progress.py`)**:
   - Enclosed image processing in `try...finally` with explicit `img.close()` on all opened bitmaps.
8. **Option Injection in Gallery-DL (`workflows/backends/gallery_dl.py`)**:
   - Inserted `--` option terminator before target URL.
9. **Hardware Acceleration VAAPI Preset Rejection (`workflows/video.py`)**:
   - Removed incompatible `-preset` flag for `vaapi`, `qsv`, and `videotoolbox`, and supplied proper hardware filters (`format=nv12,hwupload`).
10. **Rich Markup Injection Crashes (`ui/progress.py`, `ui/transcribe.py`, `ui/preview.py`)**:
    - Applied `rich.markup.escape()` to paths and error text in UI screens.
11. **Self-Corrupting Patch Script**:
    - Deleted legacy `patch_system.py`.
12. **Type Checking & CI**:
    - Fixed mypy duplicate module collisions by adding `tests/__init__.py` and configuring `explicit_package_bases = true` in `pyproject.toml`. Mypy now passes with 0 errors across 40 files.

---

## 4. Newly Identified Findings from Adversarial Review

During the second-opinion review, Codex and OpenCode identified the following remaining areas for refinement:

### 4.1 High: Console Script Wheel Packaging Mismatch
- **Location:** `pyproject.toml:73`, `cli_studio.py:22`
- **Issue:** `pyproject.toml` defines `[project.scripts] cli-studio = "cli_studio:main"`. However, setuptools packages `cli_studio.py` without `cli-studio.py` (hyphenated filenames are excluded by standard module packaging). Running `cli-studio` after `pip install .` in an external environment throws `FileNotFoundError: cli-studio.py`. (The repository's `./run.sh` and `./install` wrappers bypass this by invoking `python3 cli-studio.py` directly).
- **Remediation Plan:** Refactor entry-point architecture so `cli-studio.py` is renamed or packaged as a proper Python package module (e.g., `cli_studio/app.py`).

### 4.2 Medium: Subtitle Burn Filter Apostrophe Escaping
- **Location:** `workflows/video.py:57-68`
- **Issue:** The FFmpeg `subtitles` filter requires specific multi-level escaping for single quotes (`'`) within filter arguments. Escaping `'` as `\'` inside single-quoted filter strings causes libass to strip the quote, failing on filenames containing apostrophes (e.g., `it's.srt`).
- **Remediation Plan:** Update filter argument escaping to use `\\'\\''` or double-quoted filter definitions.

### 4.3 Low: Residual Document Help Metadata
- **Location:** `config.py:149-157`, `README.md`
- **Issue:** While document workflow files and registry entries were deleted, orphaned descriptions for Pandoc/QPDF remain in `HELP_REGISTRY` and `README.md`.
- **Remediation Plan:** Purge remaining dead document keys from `HELP_REGISTRY` and update documentation to reflect 62 tools.

---

## 5. Scope & Architecture Status

- **Focus:** Dedicated media manipulation (Video, Audio, Image) and Cloud Storage.
- **Active Tool Count:** 62 verified CLI tools in `COMMAND_REGISTRY` (down from 74 after eliminating 12 document tools).
- **Test Suite:** 134 automated unit and integration tests passing (`pytest`).
- **Type Safety:** 0 mypy errors across 40 source files.
- **Design System & CSS:** 100% intact. No styling modifications were made to `studio_themes.py` or Textual stylesheets.
- **Emoji Policy:** Clean zero-emoji verification across all codebase files, logs, and markdown.

---

## 6. Future Features & Long-Term Roadmap

1. **Package Architecture Overhaul:**
   - Migrate top-level script files into a clean `cli_studio/` namespace package to enable seamless `pip install .` and PyPI distribution.
2. **Unified Asynchronous Process Execution Engine:**
   - Consolidate all subprocess runners into an async engine using `asyncio.create_subprocess_exec` with process group isolation (`os.killpg`) to ensure zero orphaned workers.
3. **Strict Path Normalization:**
   - Enforce `os.path.realpath(os.path.expanduser(path))` across all validators to prevent symlink traversal and handle tilde inputs consistently.
4. **Enhanced Hardware Acceleration Profiles:**
   - Dynamic GPU probing (NVENC, QSV, VAAPI, VideoToolbox) with automatic fallback to software x264/x265.
