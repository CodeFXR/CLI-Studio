#!/usr/bin/env bash

set -euo pipefail

if ! infocmp "$TERM" >/dev/null 2>&1; then
    export TERM=xterm-256color
fi

# Refuse to run as root: this script touches only the user's venv.
if [ "$(id -u)" -eq 0 ]; then
    echo ":: Refusing to run as root. Run update.sh as the user who owns the install." >&2
    exit 1
fi

# Locate Python 3.10+ — required by textual>=0.85 and friends.
if ! command -v python3 >/dev/null 2>&1; then
    echo ":: python3 is required." >&2
    exit 1
fi

PYTHON_BIN="$(command -v python3)"
PY_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[0])')"
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[1])')"
PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
if [ "$PY_MAJOR" -lt 3 ] \
    || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo ":: Python 3.10 or later is required (found $PY_VERSION)." >&2
    exit 1
fi

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/cli-studio}"
VENV_DIR="$INSTALL_DIR/.venv"

CYAN="\033[36m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

PYTHON_PACKAGES=(
    "textual>=0.85,<7.0"
    "textual-image>=0.10,<2.0"
    "Pillow>=10.0,<12.0"
    "yt-dlp>=2024.1.1"
    "natsort>=8.0,<10.0"
)

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}${BOLD}Error:${RESET} No CLI-Studio installation found at $INSTALL_DIR"
    echo "Run the installer first:"
    echo "  curl -fsSL https://cso.codefxr.com/install | bash"
    exit 1
fi

echo -e "${CYAN}${BOLD}Updating CLI-Studio Python packages...${RESET}"
echo

source "$VENV_DIR/bin/activate"
pip install --upgrade "${PYTHON_PACKAGES[@]}"
echo
echo -e "${BOLD}Updating optional Python packages (ffmpeg-normalize, gallery-dl)...${RESET}"
if pip install --quiet --upgrade ffmpeg-normalize gallery-dl; then
    :
else
    echo -e "${YELLOW}Warning:${RESET} Optional Python packages failed to install."
    echo -e "${YELLOW}         Normalize Audio (2-pass) and Download Gallery will not work."
    echo -e "${YELLOW}         Re-run this installer or: pip install ffmpeg-normalize gallery-dl${RESET}"
fi

echo
echo -e "${GREEN}${BOLD}[OK] Python packages updated.${RESET}"
echo
echo -e "${BOLD}Note:${RESET} ffmpeg, ImageMagick, ExifTool, and chafa are system packages."
echo "Update them with your package manager:"
echo
echo -e "  ${YELLOW}Fedora:${RESET}   sudo dnf upgrade ffmpeg ImageMagick perl-Image-ExifTool chafa"
echo -e "  ${YELLOW}Ubuntu:${RESET}   sudo apt upgrade ffmpeg imagemagick libimage-exiftool-perl chafa"
echo -e "  ${YELLOW}Arch:${RESET}     sudo pacman -Syu ffmpeg imagemagick perl-image-exiftool chafa"
echo -e "  ${YELLOW}macOS:${RESET}    brew upgrade ffmpeg imagemagick exiftool chafa"
