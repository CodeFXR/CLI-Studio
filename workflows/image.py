import os
from typing import cast

from natsort import natsorted

from config import validate_coords, validate_decimal, validate_dimensions, validate_exif_tag
from ui.progress import GenericCliProgressScreen, PillowProgressScreen
from ui.screens import FilePickerScreen, OptionSelectScreen, TextInputScreen
from workflows.backends import ImageMagickBackend, get_backend
from workflows.shared import file_file_progress_flow
from workflows.utils import IMAGE_EXTENSIONS as _BATCH_IMAGE_EXTS


def build_convert_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = ["png", "jpg", "webp", "bmp", "gif"]
        return OptionSelectScreen("Select Target Format:", opts, state, step3)

    def step3(fmt, state):
        state["fmt"] = fmt
        base = os.path.splitext(state["in_file"])[0]
        return FilePickerScreen("Save As (or batch dir):", f"{base}_converted.{fmt}", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "convert", target_ext=state["fmt"])

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_resize_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen(
            "Enter Dimensions (WxH):", "e.g. 1920x1080", "1920x1080", state, step3
        )

    def step3(dims, state):
        w, h = validate_dimensions(dims)
        state["dims"] = (w, h)
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{w}x{h}{ext}", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "resize", state.get("dims"))

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_crop_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen(
            "Crop Box (Left,Top,Right,Bottom):", "e.g. 0,0,500,500", "0,0,500,500", state, step3
        )

    def step3(coords, state):
        left, top, right, bottom = validate_coords(coords)
        state["dims"] = (left, top, right, bottom)
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_cropped{ext}", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "crop", state.get("dims"))

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_rotate_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = ["90 (Clockwise)", "180", "270 (Counter-Clockwise)"]
        return OptionSelectScreen("Select Rotation:", opts, state, step3)

    def step3(deg_str, state):
        state["dims"] = int(deg_str.split(" ")[0])
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen(
            "Save As (or batch dir):", f"{base}_rot{state['dims']}{ext}", state, step4
        )

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "rotate", state["dims"])

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_flip_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return OptionSelectScreen(
            "Select Flip Direction:", ["horizontal", "vertical"], state, step3
        )

    def step3(direction, state):
        state["dims"] = direction
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen(
            "Save As (or batch dir):", f"{base}_{direction[:3]}{ext}", state, step4
        )

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "flip", state["dims"])

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_remove_bg_color_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = ["white", "black", "gray", "red", "green", "blue", "yellow", "magenta", "cyan"]
        return OptionSelectScreen("Select Color to Remove:", opts, state, step3)

    def step3(color, state):
        state["color"] = color
        return TextInputScreen(
            "Tolerance/Fuzz % (e.g. 10):", "Enter percentage...", "10", state, step4
        )

    def step4(fuzz, state):
        state["fuzz"] = validate_decimal(fuzz.replace("%", ""))
        base = os.path.splitext(state["in_file"])[0]
        return FilePickerScreen(
            "Save As (MUST be .png/.webp for transparency):", f"{base}_nobg.png", state, step5
        )

    def step5(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        return GenericCliProgressScreen(
            _build_magick_cmds(
                expanded_in,
                expanded_out,
                ["-fuzz", f"{state['fuzz']}%", "-transparent", state["color"]],
            ),
            "ImageMagick",
            out_file,
        )

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_imagemagick_filter_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        opts = [
            "Grayscale (-monochrome)",
            "Sepia (-sepia-tone 80%)",
            "Negate Colors (-negate)",
            "Charcoal Sketch (-charcoal 2)",
        ]
        return OptionSelectScreen("Select Filter:", opts, state, step3)

    def step3(choice, state):
        filter_map = {
            "Grayscale (-monochrome)": ["-monochrome"],
            "Sepia (-sepia-tone 80%)": ["-sepia-tone", "80%"],
            "Negate Colors (-negate)": ["-negate"],
            "Charcoal Sketch (-charcoal 2)": ["-charcoal", "2"],
        }
        state["filter"] = filter_map[choice]
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or dir):", f"{base}_filtered{ext}", state, step4)

    def step4(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        return GenericCliProgressScreen(
            _build_magick_cmds(
                expanded_in,
                expanded_out,
                list(state["filter"]),
            ),
            "ImageMagick",
            out_file,
        )

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_exiftool_strip_flow():
    def step2(in_file, state):
        if not in_file or not in_file.strip():
            return None
        expanded_in = os.path.abspath(os.path.expanduser(in_file))
        if expanded_in in ("/", os.path.realpath(os.path.expanduser("~"))):
            return None
        cmd = ["exiftool", "-overwrite_original", "-all=", expanded_in]
        return GenericCliProgressScreen(cmd, "ExifTool", in_file)

    return FilePickerScreen("Select Media File/Dir:", "", {}, step2)


def build_text_watermark_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen("Enter Watermark Text:", "Copyright...", "Watermark", state, step3)

    def step3(text, state):
        state["text"] = text
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_wm{ext}", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "watermark", state["text"])

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_compress_image_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen("Quality (1-100):", "60", "60", state, step3)

    def step3(qual, state):
        state["qual"] = validate_decimal(qual)
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or dir):", f"{base}_opt.jpg", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(
            state["in_file"], out_file, "compress", state["qual"], target_ext="jpg"
        )

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_images_to_pdf_flow():
    def step2(in_dir, state):
        state["in_dir"] = in_dir
        return FilePickerScreen(
            "Save PDF As:", f"{os.path.expanduser('~')}/output.pdf", state, step3
        )

    def step3(out_file, state):
        return PillowProgressScreen(state["in_dir"], out_file, "to_pdf")

    return FilePickerScreen("Select Image File or Folder of Images:", "", {}, step2)


def build_add_border_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return TextInputScreen("Border Size (px):", "10", "10", state, step3)

    def step3(size, state):
        state["size"] = validate_decimal(size, min_val=0.0, max_val=4096.0)
        base, ext = os.path.splitext(state["in_file"])
        return FilePickerScreen("Save As (or dir):", f"{base}_border{ext}", state, step4)

    def step4(out_file, state):
        return PillowProgressScreen(state["in_file"], out_file, "border", state["size"])

    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)


def build_extract_text_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return OptionSelectScreen(
            "Select OCR Language:", ["eng", "deu", "fra", "spa", "ita"], state, step3
        )

    def step3(lang, state):
        state["lang"] = lang
        base, _ = os.path.splitext(state["in_file"])
        return FilePickerScreen(
            "Save Text As (tesseract appends .txt):", f"{base}.txt", state, step4
        )

    def step4(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        out_base, _ = os.path.splitext(os.path.abspath(os.path.expanduser(out_file)))
        cmd = ["tesseract", expanded_in, out_base, "-l", state["lang"]]
        return GenericCliProgressScreen(cmd, "tesseract", out_base)

    return FilePickerScreen("Select Image File:", "", {}, step2)


_EXIF_PRESET_TAGS = [
    "Copyright",
    "Artist",
    "Author",
    "Comment",
    "Description",
    "Software",
    "Make",
    "Model",
    "DateTimeOriginal",
    "UserComment",
]


def build_set_exif_tag_flow():
    def step2(in_file, state):
        state["in_file"] = in_file
        return OptionSelectScreen(
            "EXIF tag to set:", _EXIF_PRESET_TAGS + ["Custom..."], state, step3
        )

    def step3(tag, state):
        state["tag"] = tag
        if tag == "Custom...":
            return TextInputScreen(
                "Custom tag name (e.g. Copyright, XMP:City):", "Copyright", "", state, step3b
            )
        return _step_value(state)

    def step3b(tag_name, state):
        state["tag"] = validate_exif_tag(tag_name)
        return _step_value(state)

    def _step_value(state):
        return TextInputScreen("Tag value:", "your value here", "", state, step4)

    def step4(value, state):
        state["value"] = value
        return _run(state)

    def _run(state):
        expanded_in = os.path.abspath(os.path.expanduser(state["in_file"]))
        cmd = [
            "exiftool",
            "-overwrite_original",
            f"-{state['tag']}={state['value']}",
            expanded_in,
        ]
        return GenericCliProgressScreen(cmd, "ExifTool", expanded_in)

    return FilePickerScreen("Select Image File:", "", {}, step2)


def build_copy_exif_flow():
    return file_file_progress_flow(
        input_prompt="Select SOURCE image (whose EXIF to copy):",
        second_prompt="Select TARGET image (gets source's EXIF applied):",
        tool_name="ExifTool",
        cmd_builder=lambda s: [
            "exiftool",
            "-overwrite_original",
            "-tagsFromFile",
            os.path.abspath(os.path.expanduser(s["in_file"])),
            "-all:all",
            os.path.abspath(os.path.expanduser(s["second_file"])),
        ],
    )


def build_rename_by_exif_date_flow():
    """Rename a folder of images using EXIF DateTimeOriginal via `rename` (perl-rename).

    Pattern: YYYY-MM-DD_HHMMSS_originalname.ext. Operates on all images
    in the chosen folder; prompts for target folder selection.
    """

    def step2(in_dir, state):
        expanded_in = os.path.abspath(os.path.expanduser(in_dir))
        state["in_dir"] = expanded_in
        if not os.path.isdir(expanded_in):
            return None
        return FilePickerScreen(
            "Output folder (renamed copies; originals left in place):",
            f"{expanded_in}/renamed",
            state,
            step3,
        )

    def step3(out_dir, state):
        in_dir = os.path.abspath(os.path.expanduser(state["in_dir"]))
        if not os.path.isdir(in_dir):
            return None
        files = [
            f
            for f in os.listdir(in_dir)
            if f.lower().endswith(_BATCH_IMAGE_EXTS) and os.path.isfile(os.path.join(in_dir, f))
        ]
        files = natsorted(files)
        if not files:
            return None
        os.makedirs(os.path.abspath(os.path.expanduser(out_dir)), exist_ok=True)
        expanded_out = os.path.abspath(os.path.expanduser(out_dir))
        cmds = []
        for f in files:
            in_f = os.path.join(in_dir, f)
            cmds.append(
                [
                    "exiftool",
                    "-o",
                    f"{expanded_out}/",
                    "-d",
                    "%Y-%m-%d_%H%M%S",
                    "-FileName<DateTimeOriginal",
                    in_f,
                ]
            )
        if not cmds:
            return None
        return GenericCliProgressScreen(cmds, "ExifTool", expanded_out)

    return FilePickerScreen("Select Folder of Images:", "", {}, step2)


def build_scan_barcode_flow():
    """Run zbarimg to scan QR / barcodes in one or more images.

    Output: a .txt file with all decoded payloads, one per line. zbarimg's
    raw output is `[type:]payload` per detected code.
    """

    def step2(in_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(in_file))
        state["in_file"] = expanded_in
        if os.path.isdir(expanded_in):
            files = natsorted(
                [
                    f
                    for f in os.listdir(expanded_in)
                    if f.lower().endswith(_BATCH_IMAGE_EXTS)
                    and os.path.isfile(os.path.join(expanded_in, f))
                ]
            )
        else:
            files = [expanded_in]
        if not files:
            return None
        base = "scan" if os.path.isdir(expanded_in) else os.path.splitext(os.path.basename(expanded_in))[0]
        out_path = f"{os.path.expanduser('~')}/{base}_codes.txt"
        return FilePickerScreen(
            "Save scan results As (one payload per line):", out_path, state, step3
        )

    def step3(out_file, state):
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        in_path = os.path.abspath(os.path.expanduser(state["in_file"]))
        if os.path.isdir(in_path):
            files = [
                f
                for f in os.listdir(in_path)
                if f.lower().endswith(_BATCH_IMAGE_EXTS)
                and os.path.isfile(os.path.join(in_path, f))
            ]
            cmds = [
                ["zbarimg", "--quiet", "--raw", os.path.join(in_path, f)] for f in natsorted(files)
            ]
        else:
            cmds = [["zbarimg", "--quiet", "--raw", in_path]]
        if not cmds:
            return None
        return GenericCliProgressScreen(cmds, "zbarimg", expanded_out, out_file=expanded_out)

    return FilePickerScreen("Select Image File or Folder:", "", {}, step2)


_SPRITE_TILES = ["2x2", "3x3", "4x4", "5x5", "6x6", "auto (single row)"]


def build_sprite_sheet_flow():
    def step2(in_dir, state):
        state["in_dir"] = os.path.abspath(os.path.expanduser(in_dir))
        return OptionSelectScreen("Tile grid:", _SPRITE_TILES, state, step3)

    def step3(tile, state):
        state["tile"] = tile
        return FilePickerScreen(
            "Save sprite sheet As:",
            f"{os.path.expanduser('~')}/spritesheet.png",
            state,
            step4,
        )

    def step4(out_file, state):
        in_dir = os.path.abspath(os.path.expanduser(state["in_dir"]))
        if not os.path.isdir(in_dir):
            return None
        files = [
            f
            for f in os.listdir(in_dir)
            if f.lower().endswith(_BATCH_IMAGE_EXTS) and os.path.isfile(os.path.join(in_dir, f))
        ]
        files = natsorted(files)
        if not files:
            return None
        tile_arg = state["tile"]
        if tile_arg == "auto (single row)":
            tile_value = f"{len(files)}x1"
        else:
            tile_value = tile_arg
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        backend = cast(ImageMagickBackend, get_backend("imagemagick"))
        cmd = backend.build_montage_command(
            [os.path.join(in_dir, f) for f in files],
            tile_value,
            expanded_out,
        )
        return GenericCliProgressScreen(cmd, "ImageMagick", expanded_out)

    return FilePickerScreen("Select Folder of Images:", "", {}, step2)


def _build_magick_cmds(in_path: str, out_path: str, between_args: list) -> list[list[str]]:
    backend = cast(ImageMagickBackend, get_backend("imagemagick"))
    return backend.build_commands(in_path, out_path, between_args)
