"""Tests for ConfigManager singleton with YAML persistence."""

import os
import sys
import tempfile

from PySide6.QtCore import QCoreApplication

from island_ui.config_manager import ConfigManager


def test_load_default_values():
    """ConfigManager with no file loads defaults."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    assert cm.get("island.animation_enabled") is True
    assert cm.get("island.compact_timeout_ms") == 5000


def test_set_and_get():
    """set() changes value, get() retrieves it."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    cm.set("island.compact_timeout_ms", 3000)
    assert cm.get("island.compact_timeout_ms") == 3000

    cm.set("theme.id", "dark")
    assert cm.get("theme.id") == "dark"


def test_save_and_reload():
    """set a value, save(), create new ConfigManager from same path,
    verify value persisted."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        f.write("island:\n  position: top-center\n")
        path = f.name

    try:
        cm1 = ConfigManager(config_path=path)
        cm1.set("island.compact_timeout_ms", 2500)
        cm1.save()

        cm2 = ConfigManager(config_path=path)
        assert cm2.get("island.compact_timeout_ms") == 2500
        assert cm2.get("island.position") == "top-center"
    finally:
        os.unlink(path)


def test_signal_emitted_on_change():
    """config_changed signal emits (key, value) on set()."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    received = []

    def slot(key, value):
        received.append((key, value))

    cm.config_changed.connect(slot)
    cm.set("island.animation_enabled", False)

    assert len(received) == 1
    assert received[0] == ("island.animation_enabled", False)


def test_get_with_default():
    """get() returns the provided default for missing keys."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    assert cm.get("nonexistent.key", "fallback") == "fallback"


def test_reset_to_defaults():
    """reset_to_defaults() restores all values to defaults."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    cm.set("island.compact_timeout_ms", 9999)
    cm.reset_to_defaults()

    assert cm.get("island.compact_timeout_ms") == 5000


def test_get_missing_nested_key():
    """get() returns None for a missing nested key."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    assert cm.get("island.nonexistent") is None


def test_save_no_path():
    """save() does not crash when config_path is None."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    cm = ConfigManager(config_path=None)

    cm.save()
