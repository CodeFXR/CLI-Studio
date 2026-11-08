import hashlib
import importlib.util
import logging
from collections.abc import Callable, MutableMapping
from pathlib import Path
from types import ModuleType
from typing import Any


logger = logging.getLogger(__name__)
CommandBuilder = Callable[[], Any]


def _module_name(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:12]
    return f"cli_studio_plugin_{path.stem}_{digest}"


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(_module_name(path), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create a module for {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _menu_key(value: str) -> str:
    aliases = {
        "video tools": "video",
        "audio tools": "audio",
        "image tools": "image",
        "cloud tools": "cloud",
        "device presets": "devices",
    }
    normalized = value.strip().lower()
    return aliases.get(normalized, normalized)


def _add_menu_item(menus: MutableMapping[str, list[str]], menu: str, label: str) -> None:
    items = menus.setdefault(menu, [])
    if label not in items:
        items.append(label)
    if menu == "plugins":
        main_items = menus.setdefault("main", [])
        if "Plugins" not in main_items:
            main_items.append("Plugins")


def load_plugins(
    registry: MutableMapping[str, CommandBuilder],
    plugin_dir: str | Path | None = None,
    *,
    menus: MutableMapping[str, list[str]] | None = None,
    help_registry: MutableMapping[str, str] | None = None,
) -> int:
    if plugin_dir is None:
        try:
            import config
            enabled = config.coerce_bool(
                config._load_full_config().get("enable_plugins"), default=False
            )
        except Exception:
            enabled = False
        if not enabled:
            logger.info(
                "Plugin loading disabled by default for security; set enable_plugins=True in config to enable."
            )
            return 0

    directory = (
        Path(plugin_dir).expanduser()
        if plugin_dir is not None
        else Path.home() / ".cli-studio" / "plugins"
    )
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.warning("Could not create plugin directory %s", directory)
        return 0

    loaded = 0
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith((".", "_")):
            continue
        try:
            module = _load_module(path)
            entries = getattr(module, "PLUGIN_REGISTRY", {})
            if not isinstance(entries, dict):
                raise TypeError("PLUGIN_REGISTRY must be a dictionary")
            menu = _menu_key(getattr(module, "PLUGIN_MENU", "plugins"))
            plugin_help = getattr(module, "PLUGIN_HELP", {})
            if not isinstance(plugin_help, dict):
                plugin_help = {}
            added_labels: list[str] = []
            for raw_name, builder in entries.items():
                if not isinstance(raw_name, str) or not callable(builder):
                    continue
                name = raw_name.strip().lower()
                if not name or name in registry:
                    continue
                registry[name] = builder
                added_labels.append(raw_name.strip())
                if help_registry is not None:
                    help_text = plugin_help.get(raw_name, plugin_help.get(name))
                    if (
                        isinstance(help_text, str)
                        and help_text.strip()
                        and name not in help_registry
                    ):
                        help_registry[name] = help_text.strip()
                loaded += 1
            if menus is not None:
                for label in added_labels:
                    _add_menu_item(menus, menu, label)
        except Exception:
            logger.warning("Could not load plugin %s", path)
    return loaded
