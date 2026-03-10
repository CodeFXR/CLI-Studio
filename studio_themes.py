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
#confirm-dialog, #input-dialog, #progress-dialog { 
    width: 60; 
    height: auto; 
    layout: vertical; 
    align: center middle; 
    padding: 1 2; 
}

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

THEME_ORDER = ["t-default", "t-modern", "t-too-modern", "t-coppice", "t-hunter", "t-accident", "t-bleu-gris", "t-pink"]
THEME_NAMES = {"t-default": "original", "t-modern": "modern", "t-too-modern": "too modern", "t-coppice": "coppice", "t-hunter": "hunter", "t-accident": "navy", "t-bleu-gris": "gris", "t-pink": "pink"}
NAME_TO_CLASS = {v.lower(): k for k, v in THEME_NAMES.items()}

THEMES_CSS = """
/* ---------- Original (Green) ---------- */
Screen.t-default { background: #1e1e2e; }
ModalScreen.t-default { background: rgba(0,0,0, 0.5); border: none; }
.t-default #confirm-dialog, .t-default #input-dialog, .t-default #progress-dialog { background: #24283b; border: none; }
.t-default #logo { color: #00a9ae; }
.t-default #version { color: #565f89; }
.t-default #help-text, .t-default #output-text, .t-default #input-label, .t-default #task-label, .t-default #status-label { color: #c0caf5; }
.t-default #input-container, .t-default #themes-panel, .t-default #menu-panel, .t-default #about-panel { background: #24283b; border: tall #414868; }
.t-default #themes-nav, .t-default #themes-title, .t-default #menu-nav, .t-default #menu-title, .t-default #about-title, .t-default #about-text, .t-default #about-nav { color: #c0caf5; }
.t-default #prompt, .t-default .confirm-option.selected { color: #00dadf; }
.t-default #input-label, .t-default #confirm-question, .t-default .confirm-option, .t-default #confirm-help { color: #c0caf5; }
.t-default #input-dialog Input { border: tall #565f89; }
.t-default #input-dialog Input:focus { border: tall #00dadf; }
.t-default Bar > .bar--complete { color: #00dadf; background: #00dadf; }
.t-default Toast { background: #24283b; color: #c0caf5; border: tall #414868; }
.t-default ToastTitle { color: #00dadf; text-style: bold; }

/* ---------- Modern Color Palette ---------- */
Screen.t-modern { background: #003f54; }
ModalScreen.t-modern { background: rgba(0,0,0, 0.5); border: none; }
.t-modern #confirm-dialog, .t-modern #input-dialog, .t-modern #progress-dialog { background: #006699; border: none; }
.t-modern #logo { color: #00a8cc; }
.t-modern #version { color: #d9e8f5; }
.t-modern #help-text, .t-modern #output-text, .t-modern #input-label, .t-modern #task-label { color: #d9e8f5; }
.t-modern #input-container, .t-modern #themes-panel, .t-modern #menu-panel, .t-modern #about-panel { background: #006699; border: tall #00a8cc; }
.t-modern #themes-nav, .t-modern #themes-title, .t-modern #menu-nav, .t-modern #menu-title, .t-modern #about-title, .t-modern #about-text, .t-modern #about-nav { color: #d9e8f5; }
.t-modern #prompt, .t-modern .confirm-option.selected { color: #ff6600; }
.t-modern #input-label, .t-modern #confirm-question, .t-modern .confirm-option, .t-modern #confirm-help { color: #d9e8f5; }
.t-modern #input-dialog Input { border: tall #d9e8f5; }
.t-modern #input-dialog Input:focus { border: tall #00a8cc; }
.t-modern Bar > .bar--complete { color: #00a8cc; background: #00a8cc; }
.t-modern Toast { background: #006699; color: #d9e8f5; border: tall #00a8cc; }
.t-modern ToastTitle { color: #ff6600; text-style: bold; }

/* ---------- Too Modern ---------- */
Screen.t-too-modern { background: #323a45; }
ModalScreen.t-too-modern { background: rgba(0,0,0, 0.5); border: none; }
.t-too-modern #confirm-dialog, .t-too-modern #input-dialog, .t-too-modern #progress-dialog { background: #3f6184; border: none; }
.t-too-modern #logo { color: #5faeb6; }
.t-too-modern #version { color: #f6f7f9; }
.t-too-modern #help-text, .t-too-modern #output-text, .t-too-modern #input-label, .t-too-modern #task-label { color: #f6f7f9; }
.t-too-modern #input-container, .t-too-modern #themes-panel, .t-too-modern #menu-panel, .t-too-modern #about-panel { background: #3f6184; border: tall #778899; }
.t-too-modern #themes-nav, .t-too-modern #themes-title, .t-too-modern #menu-nav, .t-too-modern #menu-title, .t-too-modern #about-title, .t-too-modern #about-text, .t-too-modern #about-nav { color: #f6f7f9; }
.t-too-modern #prompt, .t-too-modern .confirm-option.selected { color: #5faeb6; }
.t-too-modern #input-label, .t-too-modern #confirm-question, .t-too-modern .confirm-option, .t-too-modern #confirm-help { color: #f6f7f9; }
.t-too-modern #input-dialog Input { border: tall #f6f7f9; }
.t-too-modern #input-dialog Input:focus { border: tall #5faeb6; }
.t-too-modern Bar > .bar--complete { color: #5faeb6; background: #5faeb6; }
.t-too-modern Toast { background: #3f6184; color: #f6f7f9; border: tall #778899; }
.t-too-modern ToastTitle { color: #5faeb6; text-style: bold; }

/* ---------- Coppice ---------- */
Screen.t-coppice { background: #2d3037; }
ModalScreen.t-coppice { background: rgba(0,0,0, 0.5); border: none; }
.t-coppice #confirm-dialog, .t-coppice #input-dialog, .t-coppice #progress-dialog { background: #2d4440; border: none; }
.t-coppice #logo { color: #3f6567; }
.t-coppice #version { color: #f6f7f9; }
.t-coppice #help-text, .t-coppice #output-text, .t-coppice #input-label, .t-coppice #task-label { color: #f6f7f9; }
.t-coppice #input-container, .t-coppice #themes-panel, .t-coppice #menu-panel, .t-coppice #about-panel { background: #2d4440; border: tall #354e54; }
.t-coppice #themes-nav, .t-coppice #themes-title, .t-coppice #menu-nav, .t-coppice #menu-title, .t-coppice #about-title, .t-coppice #about-text, .t-coppice #about-nav { color: #f6f7f9; }
.t-coppice #prompt, .t-coppice .confirm-option.selected { color: #356f72; }
.t-coppice #input-label, .t-coppice #confirm-question, .t-coppice .confirm-option, .t-coppice #confirm-help { color: #f6f7f9; }
.t-coppice #input-dialog Input { border: tall #f6f7f9; }
.t-coppice #input-dialog Input:focus { border: tall #356f72; }
.t-coppice Bar > .bar--complete { color: #356f72; background: #356f72; }
.t-coppice Toast { background: #2d4440; color: #f6f7f9; border: tall #354e54; }
.t-coppice ToastTitle { color: #356f72; text-style: bold; }

/* ---------- Hunter ---------- */
Screen.t-hunter { background: #2a3d47; }
ModalScreen.t-hunter { background: rgba(0,0,0, 0.5); border: none; }
.t-hunter #confirm-dialog, .t-hunter #input-dialog, .t-hunter #progress-dialog { background: #3e474f; border: none; }
.t-hunter #logo { color: #47763d; }
.t-hunter #version { color: #838f9b; }
.t-hunter #help-text, .t-hunter #output-text, .t-hunter #input-label, .t-hunter #task-label { color: #838f9b; }
.t-hunter #input-container, .t-hunter #themes-panel, .t-hunter #menu-panel, .t-hunter #about-panel { background: #3e474f; border: tall #646f79; }
.t-hunter #themes-nav, .t-hunter #themes-title, .t-hunter #menu-nav, .t-hunter #menu-title, .t-hunter #about-title, .t-hunter #about-text, .t-hunter #about-nav { color: #838f9b; }
.t-hunter #prompt, .t-hunter .confirm-option.selected { color: #47763d; }
.t-hunter #input-label, .t-hunter #confirm-question, .t-hunter .confirm-option, .t-hunter #confirm-help { color: #838f9b; }
.t-hunter #input-dialog Input { border: tall #838f9b; }
.t-hunter #input-dialog Input:focus { border: tall #47763d; }
.t-hunter Bar > .bar--complete { color: #47763d; background: #47763d; }
.t-hunter Toast { background: #3e474f; color: #838f9b; border: tall #646f79; }
.t-hunter ToastTitle { color: #47763d; text-style: bold; }

/* ---------- Accident ---------- */
Screen.t-accident { background: #182c40; }
ModalScreen.t-accident { background: rgba(0,0,0, 0.5); border: none; }
.t-accident #confirm-dialog, .t-accident #input-dialog, .t-accident #progress-dialog { background: #20374e; border: none; }
.t-accident #logo { color: #5e768d; }
.t-accident #version { color: #435c74; }
.t-accident #help-text, .t-accident #output-text, .t-accident #input-label, .t-accident #task-label { color: #435c74; }
.t-accident #input-container, .t-accident #themes-panel, .t-accident #menu-panel, .t-accident #about-panel { background: #20374e; border: tall #28415b; }
.t-accident #themes-nav, .t-accident #themes-title, .t-accident #menu-nav, .t-accident #menu-title, .t-accident #about-title, .t-accident #about-text, .t-accident #about-nav { color: #435c74; }
.t-accident #prompt, .t-accident .confirm-option.selected { color: #5e768d; }
.t-accident #input-label, .t-accident #confirm-question, .t-accident .confirm-option, .t-accident #confirm-help { color: #435c74; }
.t-accident #input-dialog Input { border: tall #435c74; }
.t-accident #input-dialog Input:focus { border: tall #5e768d; }
.t-accident Bar > .bar--complete { color: #5e768d; background: #5e768d; }
.t-accident Toast { background: #20374e; color: #435c74; border: tall #28415b; }
.t-accident ToastTitle { color: #5e768d; text-style: bold; }

/* ---------- Bleu Gris ---------- */
Screen.t-bleu-gris { background: #111822; }
ModalScreen.t-bleu-gris { background: rgba(0,0,0, 0.5); border: none; }
.t-bleu-gris #confirm-dialog, .t-bleu-gris #input-dialog, .t-bleu-gris #progress-dialog { background: #191d27; border: none; }
.t-bleu-gris #logo { color: #263342; }
.t-bleu-gris #version { color: #303f50; }
.t-bleu-gris #help-text, .t-bleu-gris #output-text, .t-bleu-gris #input-label, .t-bleu-gris #task-label { color: #303f50; }
.t-bleu-gris #input-container, .t-bleu-gris #themes-panel, .t-bleu-gris #menu-panel, .t-bleu-gris #about-panel { background: #191d27; border: tall #263342; }
.t-bleu-gris #themes-nav, .t-bleu-gris #themes-title, .t-bleu-gris #menu-nav, .t-bleu-gris #menu-title, .t-bleu-gris #about-title, .t-bleu-gris #about-text, .t-bleu-gris #about-nav { color: #303f50; }
.t-bleu-gris #prompt, .t-bleu-gris .confirm-option.selected { color: #3f5f70; }
.t-bleu-gris #input-label, .t-bleu-gris #confirm-question, .t-bleu-gris .confirm-option, .t-bleu-gris #confirm-help { color: #303f50; }
.t-bleu-gris #input-dialog Input { border: tall #303f50; }
.t-bleu-gris #input-dialog Input:focus { border: tall #3f5f70; }
.t-bleu-gris Bar > .bar--complete { color: #3f5f70; background: #3f5f70; }
.t-bleu-gris Toast { background: #191d27; color: #303f50; border: tall #263342; }
.t-bleu-gris ToastTitle { color: #3f5f70; text-style: bold; }

/* ---------- Pink ---------- */
Screen.t-pink { background: #16537e; }
ModalScreen.t-pink { background: rgba(0,0,0, 0.5); border: none; }
.t-pink #confirm-dialog, .t-pink #input-dialog, .t-pink #progress-dialog { background: #1f6a9e; border: none; }
.t-pink #logo { color: #ac86be; }
.t-pink #version { color: #e0e0e0; }
.t-pink #help-text, .t-pink #output-text, .t-pink #input-label, .t-pink #task-label { color: #e0e0e0; }
.t-pink #input-container, .t-pink #themes-panel, .t-pink #menu-panel, .t-pink #about-panel { background: #1f6a9e; border: tall #6c59b2; }
.t-pink #themes-nav, .t-pink #themes-title, .t-pink #menu-nav, .t-pink #menu-title, .t-pink #about-title, .t-pink #about-text, .t-pink #about-nav { color: #e0e0e0; }
.t-pink #prompt, .t-pink .confirm-option.selected { color: #edbfd5; }
.t-pink #input-label, .t-pink #confirm-question, .t-pink .confirm-option, .t-pink #confirm-help { color: #e0e0e0; }
.t-pink #input-dialog Input { border: tall #e0e0e0; }
.t-pink #input-dialog Input:focus { border: tall #edbfd5; }
.t-pink Bar > .bar--complete { color: #edbfd5; background: #edbfd5; }
.t-pink Toast { background: #1f6a9e; color: #e0e0e0; border: tall #6c59b2; }
.t-pink ToastTitle { color: #edbfd5; text-style: bold; }
"""
