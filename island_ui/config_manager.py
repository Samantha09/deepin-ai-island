"""ConfigManager singleton with YAML persistence."""

import sys
from typing import Any

import yaml
from PySide6.QtCore import QObject, Signal

__all__ = ["ConfigManager"]

DEFAULT_CONFIG = {
    "island": {
        "position": "top-center",
        "animation_enabled": True,
        "compact_timeout_ms": 5000,
        "expanded_max_height_ratio": 0.6,
        "position_offset_x": 0,
        "position_offset_y": 0,
    },
    "theme": {
        "id": "system",
    },
    "debug": {
        "mock_events_enabled": False,
    },
}


class ConfigManager(QObject):
    """Manages application configuration with YAML persistence.

    Supports dot-notation keys (e.g., "island.animation_enabled").
    Emits ``config_changed(key, value)`` when a value is modified.
    """

    config_changed = Signal(str, object)

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the manager.

        Args:
            config_path: Path to the YAML config file. If None or the file
                does not exist, defaults are used.
        """
        super().__init__()
        self._config_path = config_path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file, merging over defaults."""
        self._data = _deep_copy(DEFAULT_CONFIG)
        if self._config_path is not None:
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    _deep_merge(self._data, loaded)
            except FileNotFoundError:
                pass
            except yaml.YAMLError:
                print(f"Warning: malformed YAML in {self._config_path}",
                      file=sys.stderr)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value.

        Args:
            key: Dot-notation key such as ``"island.animation_enabled"``.
            default: Value to return if the key is missing.

        Returns:
            The stored value or ``default``.
        """
        parts = key.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Dot-notation key such as ``"island.animation_enabled"``.
            value: Value to store.
        """
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                # Replace non-dict intermediates so we don't crash
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
        self.config_changed.emit(key, value)

    def save(self) -> None:
        """Write the current configuration to the YAML file.

        Does nothing if no path was provided.
        """
        if self._config_path is None:
            return
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._data, f, default_flow_style=False,
                               allow_unicode=True, sort_keys=False)
        except OSError:
            pass

    def reset_to_defaults(self) -> None:
        """Restore all values to defaults and emit a wildcard signal."""
        self._data = _deep_copy(DEFAULT_CONFIG)
        self.config_changed.emit("*", None)


def _deep_copy(obj: Any) -> Any:
    """Return a deep copy of a dict/list structure."""
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Merge ``overlay`` into ``base`` in place."""
    for key, value in overlay.items():
        if (key in base and isinstance(base[key], dict)
                and isinstance(value, dict)):
            _deep_merge(base[key], value)
        else:
            base[key] = value
