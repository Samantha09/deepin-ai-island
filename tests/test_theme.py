"""Tests for Theme class with preset palettes."""

import sys

from PySide6.QtWidgets import QApplication, QWidget

from island_ui.theme import Theme, ThemePreset


def test_current_returns_dark_by_default():
    """Theme() current_id() == 'dark'."""
    app = QApplication.instance() or QApplication(sys.argv)
    theme = Theme()
    assert theme.current_id() == "dark"


def test_switch_preset():
    """set_preset(ThemePreset.LIGHT), current_id() == 'light', current()
    colors differ from dark."""
    app = QApplication.instance() or QApplication(sys.argv)
    theme = Theme()
    dark_colors = theme.current()

    theme.set_preset(ThemePreset.LIGHT)
    assert theme.current_id() == "light"
    light_colors = theme.current()
    assert light_colors != dark_colors


def test_apply_to_widget_changes_stylesheet():
    """apply_to_widget(widget) sets a styleSheet with background-color."""
    app = QApplication.instance() or QApplication(sys.argv)
    theme = Theme()
    widget = QWidget()
    theme.apply_to_widget(widget)
    sheet = widget.styleSheet()
    assert "background-color" in sheet
