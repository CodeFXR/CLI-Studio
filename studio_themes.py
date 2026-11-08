LAYOUT_CSS = """
/* Global Alignment */
Screen { 
    layout: vertical; 
    align: center middle;
    background: transparent; 
}

Container, Static { background: transparent; border: none; }

/* Main Container */
#main-container { width: 60%; height: auto; layout: vertical; align: center middle; padding: 1; }
#stage { width: 100%; height: auto; layout: vertical; align: center middle; }

/* Logo */
Center { width: 100%; height: auto; align: center middle; margin-bottom: 0; }
#logo { width: auto; height: 10; margin: 0 0 1 0; }
#version { width: 100%; height: 0; content-align: center middle; margin: 0; display: none; }
#output-text { width: 100%; content-align: center middle; height: 1; margin: 0; }

/* Content Zone */
#content-zone { width: 100%; height: 10; align: center middle; margin-bottom: 1; }

Screen.themes-open #logo, Screen.themes-open Center,
Screen.expanded-view #logo, Screen.expanded-view Center { display: none; }

Screen.themes-open #content-zone,
Screen.expanded-view #content-zone { height: 21; }

/* Help text */
#help-text { width: 100%; height: 100%; content-align: center middle; }

/* Panels */
#about-panel, #menu-panel, #themes-panel { width: 100%; display: none; layout: vertical; height: 100%; align: center top; }
#about-title, #menu-title, #themes-title { height: 1; content-align: center middle; margin: 0; text-style: bold; }
#about-text, #menu-list, #themes-list { width: 100%; height: 1fr; content-align: left top; padding: 0 2; }
#menu-list, #themes-list { text-align: center; background: transparent; border: none; scrollbar-size-vertical: 0; }
#about-nav, #menu-nav, #themes-nav { height: 1; content-align: center middle; margin: 0; }

/* Input Row */
#input-container { width: 100%; height: 3; layout: horizontal; margin: 0; }
#prompt { width: auto; height: 1; margin-right: 1; align-vertical: middle; padding-left: 1; }
#user-input { width: 1fr; height: 1; border: none; background: transparent; padding: 0; margin: 0; align-vertical: middle; }
#user-input:focus { border: none; }

/* Footer */
#footer { width: 100%; height: 1; margin: 0; layout: horizontal; }
#input-label { width: auto; content-align: left middle; padding-left: 1; }

/* View Toggles */
Screen.themes-open #help-text { display: none; }
Screen.themes-open #themes-panel { display: block; }
Screen.about-open #help-text { display: none; }
Screen.about-open #about-panel { display: block; }
Screen.menu-open #help-text { display: none; }
Screen.menu-open #menu-panel { display: block; }
Screen.log-open #help-text { display: none; }
Screen.log-open #terminal-log { display: block; }

#terminal-log {
    width: 100%;
    height: 100%;
    display: none;
    border: tall #888888;
    background: transparent;
    padding: 0 1;
}
#help-body {
    width: 100%;
    margin: 1 0;
    content-align: center middle;
    color: #cccccc;
}


/* OptionList Visuals */
OptionList > * { height: 1; content-align: center middle; padding: 0; margin: 0; width: 100%; }
OptionList:focus > .option-list--option-highlighted { text-style: bold; }

/* --- MODAL STYLING --- */
ModalScreen {
    align: center middle; 
    background: rgba(0,0,0, 0.5); 
    border: none;
}

/* The Box */
#confirm-dialog, #input-dialog, #progress-dialog, #preview-dialog { 
    width: 60; 
    height: auto; 
    layout: vertical; 
    align: center middle; 
    padding: 1 2; 
}
#preview-dialog { width: 82; }
#preview-title { width: 100%; height: 1; content-align: center middle; text-style: bold; margin-bottom: 1; }
#preview-content { width: 100%; height: 20; content-align: left top; overflow: hidden; }
#preview-help { width: 100%; height: 2; content-align: center middle; margin-top: 1; }

/* Transparent Inputs inside Modals */
#input-dialog Input {
    background: transparent;
    border: tall #888888;
}
#input-dialog Input:focus {
    border: tall #ffffff;
}

/* Text & Progress */
#confirm-question, #input-label, #task-label { width: 100%; content-align: center middle; text-style: bold; margin-bottom: 1; }
#input-sublabel { width: 100%; content-align: center middle; color: #888888; margin-top: 1; }
#status-label { width: 100%; content-align: center middle; color: #888888; }
ProgressBar { width: 100%; margin: 1 0; }
Bar > .bar--bar { color: #888888; background: #333333; }
Bar > .bar--complete { color: #ffffff; background: #ffffff; }

#confirm-spacer, #confirm-spacer2 { width: 100%; height: 1; }
#confirm-options { width: 100%; height: auto; layout: horizontal; align: center middle; }
.confirm-option { width: auto; height: auto; content-align: center middle; padding: 0 4; }
#confirm-help { width: 100%; height: auto; content-align: center middle; }

/* --- NOTIFICATIONS (Global) --- */
Toast {
    min-width: 30;
    width: auto;
    padding: 1 2;
    margin-bottom: 1;
}
"""

THEME_ORDER = [
    "t-default",
    "t-modern",
    "t-too-modern",
    "t-coppice",
    "t-hunter",
    "t-accident",
    "t-bleu-gris",
    "t-pink",
]
THEME_NAMES = {
    "t-default": "original",
    "t-modern": "modern",
    "t-too-modern": "too modern",
    "t-coppice": "coppice",
    "t-hunter": "hunter",
    "t-accident": "navy",
    "t-bleu-gris": "gris",
    "t-pink": "pink",
}
NAME_TO_CLASS = {v.lower(): k for k, v in THEME_NAMES.items()}


def log_palette_colors(theme_class: str) -> tuple[str, str]:
    """Return (accent, fail) Rich color hex strings for a theme class.

    `accent` is the theme's own accent (varies per theme); `fail` is a
    universal warning red chosen to read on every dark palette.
    """
    palette = THEME_PALETTES.get(theme_class) or THEME_PALETTES["t-default"]
    return str(palette["accent"]), "#f7768e"


THEME_PALETTES = {
    "t-default": {
        "bg": "#1e1e2e",
        "panel": "#24283b",
        "panel_border": "#414868",
        "logo": "#00a9ae",
        "version": "#565f89",
        "text": "#c0caf5",
        "accent": "#00dadf",
        "highlight": "#00dadf",
        "input_border": "#565f89",
        "status_in_help": True,
    },
    "t-modern": {
        "bg": "#003f54",
        "panel": "#006699",
        "panel_border": "#00a8cc",
        "logo": "#00a8cc",
        "version": "#d9e8f5",
        "text": "#d9e8f5",
        "accent": "#ff6600",
        "highlight": "#00a8cc",
        "input_border": "#d9e8f5",
        "status_in_help": False,
    },
    "t-too-modern": {
        "bg": "#323a45",
        "panel": "#3f6184",
        "panel_border": "#778899",
        "logo": "#5faeb6",
        "version": "#f6f7f9",
        "text": "#f6f7f9",
        "accent": "#5faeb6",
        "highlight": "#5faeb6",
        "input_border": "#f6f7f9",
        "status_in_help": False,
    },
    "t-coppice": {
        "bg": "#2d3037",
        "panel": "#2d4440",
        "panel_border": "#354e54",
        "logo": "#3f6567",
        "version": "#f6f7f9",
        "text": "#f6f7f9",
        "accent": "#356f72",
        "highlight": "#356f72",
        "input_border": "#f6f7f9",
        "status_in_help": False,
    },
    "t-hunter": {
        "bg": "#2a3d47",
        "panel": "#3e474f",
        "panel_border": "#646f79",
        "logo": "#47763d",
        "version": "#838f9b",
        "text": "#838f9b",
        "accent": "#47763d",
        "highlight": "#47763d",
        "input_border": "#838f9b",
        "status_in_help": False,
    },
    "t-accident": {
        "bg": "#182c40",
        "panel": "#20374e",
        "panel_border": "#28415b",
        "logo": "#5e768d",
        "version": "#435c74",
        "text": "#435c74",
        "accent": "#5e768d",
        "highlight": "#5e768d",
        "input_border": "#435c74",
        "status_in_help": False,
    },
    "t-bleu-gris": {
        "bg": "#111822",
        "panel": "#191d27",
        "panel_border": "#263342",
        "logo": "#263342",
        "version": "#303f50",
        "text": "#303f50",
        "accent": "#3f5f70",
        "highlight": "#3f5f70",
        "input_border": "#303f50",
        "status_in_help": False,
    },
    "t-pink": {
        "bg": "#16537e",
        "panel": "#1f6a9e",
        "panel_border": "#6c59b2",
        "logo": "#ac86be",
        "version": "#e0e0e0",
        "text": "#e0e0e0",
        "accent": "#edbfd5",
        "highlight": "#edbfd5",
        "input_border": "#e0e0e0",
        "status_in_help": False,
    },
}


def _theme_css(name: str, p: dict) -> str:
    status_part = f", .{name} #status-label" if p["status_in_help"] else ""
    return f"""/* ---------- {THEME_NAMES[name]} ---------- */
Screen.{name} {{ background: {p["bg"]}; }}
ModalScreen.{name} {{ background: rgba(0,0,0, 0.5); border: none; }}
.{name} #confirm-dialog, .{name} #input-dialog, .{name} #progress-dialog, .{name} #preview-dialog {{ background: {p["panel"]}; border: none; }}
.{name} #logo {{ color: {p["logo"]}; }}
.{name} #version {{ color: {p["version"]}; }}
.{name} #help-text, .{name} #output-text, .{name} #input-label, .{name} #task-label{status_part} {{ color: {p["text"]}; }}
.{name} #input-container, .{name} #themes-panel, .{name} #menu-panel, .{name} #about-panel {{ background: {p["panel"]}; border: tall {p["panel_border"]}; }}
.{name} #themes-nav, .{name} #themes-title, .{name} #menu-nav, .{name} #menu-title, .{name} #about-title, .{name} #about-text, .{name} #about-nav, .{name} #preview-title, .{name} #preview-content, .{name} #preview-help {{ color: {p["text"]}; }}
.{name} #prompt, .{name} .confirm-option.selected {{ color: {p["accent"]}; }}
.{name} #input-label, .{name} #confirm-question, .{name} .confirm-option, .{name} #confirm-help {{ color: {p["text"]}; }}
.{name} #input-dialog Input {{ border: tall {p["input_border"]}; }}
.{name} #input-dialog Input:focus {{ border: tall {p["highlight"]}; }}
.{name} Bar > .bar--complete {{ color: {p["highlight"]}; background: {p["highlight"]}; }}
.{name} Toast {{ background: {p["panel"]}; color: {p["text"]}; border: tall {p["panel_border"]}; }}
.{name} ToastTitle {{ color: {p["accent"]}; text-style: bold; }}
"""


THEMES_CSS = "\n".join(_theme_css(name, THEME_PALETTES[name]) for name in THEME_ORDER)
