import os
from ui.screens import TextInputScreen, FilePickerScreen, OptionSelectScreen
from ui.progress import PillowProgressScreen, GenericCliProgressScreen

def build_convert_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["png", "jpg", "webp", "bmp", "gif"]
        return OptionSelectScreen("Select Target Format:", opts, state, step3)
    def step3(fmt, state):
        state['fmt'] = fmt
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save As (or batch dir):", f"{base}_converted.{fmt}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "convert", target_ext=state['fmt'])
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_resize_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Enter Dimensions (WxH):", "e.g. 1920x1080", "1920x1080", state, step3)
    def step3(dims, state):
        try:
            w, h = map(int, dims.lower().split('x'))
            state['dims'] = (w, h)
        except ValueError:
            raise ValueError("Invalid dimensions. Must be WxH (e.g. 1920x1080).")
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{w}x{h}{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "resize", state.get('dims'))
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_crop_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Crop Box (Left,Top,Right,Bottom):", "e.g. 0,0,500,500", "0,0,500,500", state, step3)
    def step3(coords, state):
        try:
            l, t, r, b = map(int, coords.replace(' ', '').split(','))
            state['dims'] = (l, t, r, b)
        except ValueError:
            raise ValueError("Invalid coordinates. Must be Left,Top,Right,Bottom.")
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_cropped{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "crop", state.get('dims'))
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_rotate_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["90 (Clockwise)", "180", "270 (Counter-Clockwise)"]
        return OptionSelectScreen("Select Rotation:", opts, state, step3)
    def step3(deg_str, state):
        state['dims'] = int(deg_str.split(' ')[0])
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_rot{state['dims']}{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "rotate", state['dims'])
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_flip_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return OptionSelectScreen("Select Flip Direction:", ["horizontal", "vertical"], state, step3)
    def step3(direction, state):
        state['dims'] = direction
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_{direction[:3]}{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "flip", state['dims'])
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_remove_bg_color_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = ["white", "black", "gray", "red", "green", "blue", "yellow", "magenta", "cyan"]
        return OptionSelectScreen("Select Color to Remove:", opts, state, step3)
    def step3(color, state):
        state['color'] = color
        return TextInputScreen("Tolerance/Fuzz % (e.g. 10):", "Enter percentage...", "10", state, step4)
    def step4(fuzz, state):
        state['fuzz'] = fuzz.replace('%', '')
        base = os.path.splitext(state['in_file'])[0]
        return FilePickerScreen("Save As (MUST be .png/.webp for transparency):", f"{base}_nobg.png", state, step5)
    def step5(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state['in_file']))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        cmd = ["magick", expanded_in, "-fuzz", f"{state['fuzz']}%", "-transparent", state['color'], expanded_out]
        return GenericCliProgressScreen(cmd, "ImageMagick", out_file)
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_imagemagick_filter_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        opts = [
            "Grayscale (-monochrome)", 
            "Sepia (-sepia-tone 80%)", 
            "Negate Colors (-negate)", 
            "Charcoal Sketch (-charcoal 2)"
        ]
        return OptionSelectScreen("Select Filter:", opts, state, step3)
    def step3(choice, state):
        filter_map = {
            "Grayscale (-monochrome)": ["-monochrome"],
            "Sepia (-sepia-tone 80%)": ["-sepia-tone", "80%"],
            "Negate Colors (-negate)": ["-negate"],
            "Charcoal Sketch (-charcoal 2)": ["-charcoal", "2"],
        }
        state['filter'] = filter_map[choice]
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or dir):", f"{base}_filtered{ext}", state, step4)
    def step4(out_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(state['in_file']))
        expanded_out = os.path.abspath(os.path.expanduser(out_file))
        cmd = ["magick", expanded_in] + state['filter'] + [expanded_out]
        return GenericCliProgressScreen(cmd, "ImageMagick", out_file)
    return FilePickerScreen("Select Image File:", "", {}, step2)

def build_exiftool_strip_flow():
    def step2(in_file, state):
        expanded_in = os.path.abspath(os.path.expanduser(in_file))
        cmd = ["exiftool", "-all=", expanded_in]
        return GenericCliProgressScreen(cmd, "ExifTool", in_file)
    return FilePickerScreen("Select Media File/Dir:", "", {}, step2)

def build_text_watermark_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Enter Watermark Text:", "Copyright...", "Watermark", state, step3)
    def step3(text, state):
        state['text'] = text
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or batch dir):", f"{base}_wm{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "watermark", state['text'])
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_compress_image_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Quality (1-100):", "60", "60", state, step3)
    def step3(qual, state):
        state['qual'] = qual
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or dir):", f"{base}_opt.jpg", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "compress", state['qual'], target_ext="jpg")
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)

def build_images_to_pdf_flow():
    def step2(in_dir, state):
        state['in_dir'] = in_dir
        return FilePickerScreen("Save PDF As:", f"{os.path.expanduser('~')}/output.pdf", state, step3)
    def step3(out_file, state):
        return PillowProgressScreen(state['in_dir'], out_file, "to_pdf")
    return FilePickerScreen("Select Image File or Folder of Images:", "", {}, step2)

def build_add_border_flow():
    def step2(in_file, state):
        state['in_file'] = in_file
        return TextInputScreen("Border Size (px):", "10", "10", state, step3)
    def step3(size, state):
        state['size'] = size
        base, ext = os.path.splitext(state['in_file'])
        return FilePickerScreen("Save As (or dir):", f"{base}_border{ext}", state, step4)
    def step4(out_file, state):
        return PillowProgressScreen(state['in_file'], out_file, "border", state['size'])
    return FilePickerScreen("Select Image File/Folder:", "", {}, step2)