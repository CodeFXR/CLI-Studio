# CLI-Studio — Cleanup Roadmap (Part 2)

> **Purpose.** Active working doc sequel to `CLEANUP_ROADMAP.md`. Picks up where Phase 7 left off and targets the gaps identified in `CRITICAL_ASSESSMENT_part2.md`. Ordered by ROI; each phase should end with a clean commit before moving to the next.
> **Last updated.** 2026-07-22 (Phase 19 work landed; see `CLEANUP_ROADMAP_part3.md` for the latest cleanup pass)
> **Current state.** Phases 0–17 + Phase 18 polish + Phase 19 cleanup complete; 74 tools; 151 tests pass (was 144); score 7.5/10 → 8.5/10 → 9.3/10.

---

## Where we are

- [DONE] **Phase 0–7** complete (2026-07-21) — cleanup, security, bug fixes, refactor, tests+CI, features, architecture.
- [DONE] **Feature sprint** complete — chafa preview, audiowaveform preview, Whisper subtitles, Real-ESRGAN upscaling.
- [DONE] **Phase 8–17** complete (2026-07-21) — argv validators, markup-injection fixes, exiftool overwrite, codec-aware extract subs, `file_file_in_out_flow` refactor, theme-aware log colors, install-script hardening, validator tests, help coverage, SECURITY.md.
- [DONE] **Phase 18 polish** complete (2026-07-21) — trim-batch output collision fix via `unique_path()` helper, `Backend` base class with `__init_subclass__` contract enforcement, `cli-studio.py` exports `main()`, `ruff format` applied tree-wide, 13 redundant wizard-step docstrings removed, 6 new tests (burn-subtitles-filter-metachar escape, `/themes` slash-command routing, `Backend` contract enforcement, `unique_path` collision). Score: 8.5/10.
- [DONE] **Phase 19** complete (2026-07-22) — see `CLEANUP_ROADMAP_part3.md`. PillowProgressScreen mixin fix, theme-aware "Unknown command", `update.sh` hardening, wizard exception mapping, lambda→named builders, chafa respects `ffmpeg_overwrite`, `cli-studio/` gitignore, single `IMAGE_EXTENSIONS` constant, `pip install .` entry points, dead `return v` removed, final lazy `natsort` import lifted. Score: 9.3/10.

Test count: 144 (was 138). Score: 7.5 → 8.5/10. Ruff + mypy clean.

---

## Phase 8 — Output markup hardening [DONE] done (kept `markup=True`, escaped 3 sites)

Rather than `markup=False` (which would lose the colored status text), added `escape()` to the 3 unescaped user-input sites in `cli-studio.py:_update_output` (theme-name lookup, OSError in config save, OSError in setting save). The 5 hardcoded log colors in `ui/progress.py` were replaced with `_log_msg("kind", body)` (Phase 14) which derives accent/fail from the active theme.

## Phase 9 — Argv-injection hardening [DONE] done

4 validators added (`validate_pages`, `validate_remote_name`, `validate_exif_tag`, `validate_cache_dir`) in `config.py` and wired into mutool, qpdf, rclone, exiftool-set, and Whisper cache-dir flows. Each rejects flag-like and shell-metacharacter inputs while preserving the wizard UX (modal stays open, error shown as toast).

## Phase 10 — `burn_subtitles` filter escaping [DONE] done

Extended escape in `workflows/video.py` to also cover `[`, `]`, `,`, `;`. Extracted the escape logic to `_burn_subs_filter_arg()` and refactored `build_burn_subtitles_flow` to use `file_file_in_out_flow` (Phase 13).

## Phase 11 — Strip-metadata `exiftool` overwrite [DONE] done

Added `-overwrite_original` to `build_exiftool_strip_flow`. The 1-line fix from part-1 §4.2.9 finally landed.

## Phase 12 — UX bug fixes [DONE] done (Cloud Tools, image warning, codec, rclone output)

- Removed dead `Cloud Tools` entry from `MENU_DOCUMENTS`.
- `textual-image` warning shown once per session via `_startup_warnings_shown` flag.
- `extract subtitles` probes codec via `probe_first_subtitle_codec()` and `subtitle_ext_for_codec()` (in `workflows/utils.py`), then uses `-c:s copy` to avoid silent re-encoding. Defaults to `.srt` when probe fails.
- `rclone listremotes` now writes output to a file via the new `_RcloneListRemotesScreen` (worker, atomic file write, error handling for missing rclone / timeout).
- HW-accel cycle: kept the existing 5-value cycle (UX nit, not blocking).

## Phase 13 — Refactor: `file_file_in_out_flow` + `file_file_progress_flow` helpers [DONE] done

Added two helpers to `workflows/shared.py`. Refactored 5 flows to use them: `build_burn_subtitles_flow`, `build_add_watermark_flow`, `build_add_audio_track_flow`, `build_mix_audio_flow`, `build_copy_exif_flow`. Net LOC change: roughly +20 in shared.py, −45 across the 5 flow files.

## Phase 14 — Refactor: dedup, theme colors, lazy imports [DONE] done

- 3 duplicate `_abspath` definitions consolidated into `workflows/utils.py:abspath`.
- 4 lazy `from natsort import natsorted` imports in `workflows/image.py` lifted to module top.
- `studio_themes.py:log_palette_colors(theme_class) -> (accent, fail)` added. `_LoggingModalScreen._log_msg(kind, body)` derives colors from `self.app.active_theme`. Replaced 6 hardcoded markup sites in `ui/progress.py` and `workflows/cloud.py`.
- `HelpModal` takes `theme_class` in `__init__` (or relies on `push_themed_screen`), eliminating first-paint flicker.

## Phase 15 — Install-script hardening [DONE] done (skipped curl|bash per user direction)

- `|| true` for optional Python deps replaced with a visible warning telling the user which flows will fail.
- RC append now prints the diff and prompts for `y/N` before writing.
- `curl | bash` recommendation in README/website kept (user's stated preference; project is open-source and auditable).

## Phase 16 — Test coverage [DONE] done

Added 9 new tests (was 129 → 138):
- 16 validator rejection cases (`test_validators_exist_and_reject_bad_input`).
- 8 validator acceptance cases (`test_validators_accept_good_input`).
- `test_help_registry_covers_every_command` — fails loudly if any tool lacks dedicated help text.
- `test_documents_menu_has_no_dead_section_headers` — guards the Cloud Tools regression.
- `test_menus_reference_no_unknown_commands` — catches dead menu items before they ship.
- `test_build_extract_subs_flow_probes_codec_for_ass`, `..._for_webvtt`, `..._falls_back_to_srt_when_probe_fails` — codec probing.
- `test_rclone_copy_flow_rejects_malicious_remote_name` — argv injection regression test.
- `test_extract_subs_includes_copy_codec_to_avoid_reencode` — guards the `-c:s copy` regression.

Skipped (not blocking):
- Cancellation race tests (worker thread timing is fragile to test).
- Entry-point subprocess test (Textual `run_test` covers this).
- Plugin two-collision test (covered indirectly by existing collision tests).

## Phase 17 — Documentation updates [DONE] done

- `pyproject.toml` description mentions all 14 backends; keywords expanded.
- New `SECURITY.md` documents threat model, what's hardened, what's not, plugin trust, `curl|bash` rationale.
- 23 help entries added to `HELP_REGISTRY` for tools that previously fell back to the generic template.
- `ARCHITECTURE.md` updated with "Recent cleanup (Phases 8–17)" section.

---

## Phase 18 — Architecture polish (aspirational, low priority)

For a future v1.1.

- [x] **Move from `requirements.txt` (gone) to `pyproject.toml` as the install source of truth.** ~~Done in Phase 0.~~ Not pursued further — install script's `PYTHON_PACKAGES` array kept (per user's audit-trail preference).
- [x] **Add `__main__.py`** for `python -m cli_studio` execution. **Partial.** `cli-studio.py` now exports `main()` for clean entry-point semantics; full `python -m cli_studio` requires renaming the file (which would touch the install script). Skipped.
- [x] **Document the Backend contract** in `workflows/backends/base.py` with proper ABC. **Done.** `__init_subclass__` enforces `name` and `operations` at class-definition time. Did not add `ABC` inheritance because backends have heterogeneous `__init__` signatures that don't fit a single abstract contract; the validation contract is more pragmatic.
- [ ] **Add type stubs** for the backends (`.pyi` files).
- [ ] **Replace `lambda` builders in `COMMAND_REGISTRY`** with named functions for better stack traces. **Skipped.** Lambdas are trivial wrappers over the named builders; named functions would add ceremony without runtime benefit.
- [ ] **Add a `--check` mode** that runs all wizards without executing subprocess, to catch wizard bugs in CI.

### Phase 18 actual additions (2026-07-21):

- **Trim-batch output collision fix.** `FfmpegProgressScreen` and `PillowProgressScreen` batch modes now use `workflows.utils.unique_path()` to avoid overwriting outputs when two input folders share filenames. Replaces ad-hoc inline collision code with a single helper.
- **Backend contract enforcement.** `Backend.__init_subclass__` raises `TypeError` at class-definition time if `name` or `operations` is missing. Test: `test_backend_base_enforces_name_and_operations`.
- **`main()` entry-point export.** `cli-studio.py:608` defines `main()` so future `__main__.py` or test harness can call it directly.
- **`ruff format` normalization.** 25 files reformatted, 15 unchanged; no behavior change.
- **Docstring cleanup.** 13 wizard-step docstrings removed across `workflows/video.py`, `workflows/image.py`, `workflows/mkv.py`, `workflows/mupdf.py`, `workflows/utils.py`. WHY-content docstrings preserved.
- **6 new tests.** Burn-subtitles-filter-metachar escape (`test_build_burn_subtitles_flow_escapes_ffmpeg_filter_metachars`), `/themes <name>` and `/themes <empty>` slash-command routing (3 tests), `unique_path` collision (`test_unique_path_avoids_collisions`).

---

## Progress tracking — actual commits (suggested)

If/when these get committed, recommended grouping:

- `security: escape user input in 3 _update_output sites, validate argv inputs`
- `fix: -overwrite_original for strip metadata, codec-aware extract subs, [-escape burn subtitles`
- `refactor: file_file_in_out_flow helper, dedup _abspath, theme-aware log colors`
- `feat: rclone listremotes writes to file via new screen`
- `docs: SECURITY.md, 23 help entries, ARCHITECTURE recent cleanup`
- `test: argv injection regression, help coverage, dead-menu guard`
- `polish: trim-batch unique_path collision handling, Backend ABC contract, main() export`
- `chore: ruff format, remove 13 redundant wizard-step docstrings`
- `chore: install script warns on optional deps, prompts before RC append`

---

## What I did NOT add (deliberate non-goals)

- **No new features.** The audit identified gaps in existing flows; closing them is the priority.
- **No v2.0 thinking** (sync engine, undo, real-time progress streaming). Those are post-v1.0 work.
- **No backend additions** (no new CLI wraps in this phase). The 14 backends are the right number for the threat-of-bloat.
- **No removal of the plugin system** (it's recent, low-cost, and a feature moat).
- **No `markup=False` switch on `#output-text`.** Kept markup but escaped all user input; this preserves the colored status text (`"Theme applied: navy"`, `"Unknown command: ..."`).

---

## Score delta

| Dimension | Before Phase 8–17 | After |
|---|---:|---:|
| Architecture | 8.5/10 | 8.5/10 (helpers used; ABI stable) |
| Code quality | 6/10 | 7/10 (markup consistent, lazy imports gone, theme colors, dedup) |
| Security | 6/10 | 7.5/10 (argv validators +5 sites; burn-subs escape; overwrite_original) |
| UX | 8/10 | 8.5/10 (Cloud Tools gone, codec-aware, rclone output, image warning) |
| Documentation | 5.5/10 | 6.5/10 (SECURITY.md, help entries, ARCHITECTURE refresh) |
| Testing | 7/10 | 8/10 (138 tests; argv-injection regression; coverage gaps closed) |
| Features (breadth) | 9.5/10 | 9.5/10 (unchanged — no new tools) |
| Features (depth) | 6.5/10 | 7/10 (codec-aware subs, -c:s copy, secure rclone) |
| Distribution | 5/10 | 5.5/10 (install script warns + prompts) |
| **Composite** | **7.5/10** | **8.5/10** |

This is the score the project deserves to ship as v1.0.