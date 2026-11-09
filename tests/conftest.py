import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli_studio  # noqa: E402

_cli_studio = cli_studio
sys.modules.setdefault("cli_studio_app", cli_studio)
