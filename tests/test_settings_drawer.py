"""Tests for SettingsDrawer component with Config binding."""

import sys

from PySide6.QtWidgets import QApplication

from island_ui.config_manager import ConfigManager
from island_ui.settings_drawer import SettingsDrawer


def test_drawer_has_all_controls():
    """SettingsDrawer creates all expected controls."""
    app = QApplication.instance() or QApplication(sys.argv)
    cm = ConfigManager(config_path=None)
    drawer = SettingsDrawer(cm)

    assert drawer._theme_combo is not None
    assert drawer._anim_row is not None
    assert drawer._timeout_spin is not None
    assert drawer._pos_x_spin is not None
    assert drawer._pos_y_spin is not None


def test_theme_change_emits_signal():
    """Changing theme combo emits config_changed signal."""
    app = QApplication.instance() or QApplication(sys.argv)
    cm = ConfigManager(config_path=None)
    drawer = SettingsDrawer(cm)

    received = []

    def slot(key, value):
        received.append((key, value))

    cm.config_changed.connect(slot)
    drawer._theme_combo.setCurrentText("light")

    assert ("theme.id", "light") in received


def test_reset_row_restores_defaults():
    """Clicking Reset defaults restores animation_enabled to True."""
    app = QApplication.instance() or QApplication(sys.argv)
    cm = ConfigManager(config_path=None)
    drawer = SettingsDrawer(cm)

    cm.set("island.animation_enabled", False)
    drawer._load_from_config()

    assert drawer._anim_row.is_on() is False

    # 模拟点击 Reset 行
    drawer._on_reset()

    assert cm.get("island.animation_enabled") is True
    assert drawer._anim_row.is_on() is True
