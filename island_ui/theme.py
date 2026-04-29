"""Theme management with preset color palettes."""

from enum import Enum

from PySide6.QtWidgets import QWidget


class ThemePreset(Enum):
    """Available theme presets."""
    DARK = "dark"
    LIGHT = "light"
    CLASSIC = "classic"


PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "window_bg": "#151519",
        "panel_bg": "#1e1e23",
        "card_bg": "#1e1e23",
        "primary_text": "#eeeeee",
        "secondary_text": "#888888",
        "muted_text": "#aaaaaa",
        "badge_text": "#aaaaaa",
        "border": "rgba(255, 255, 255, 0.08)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
    "light": {
        "window_bg": "#f5f5f7",
        "panel_bg": "#ffffff",
        "card_bg": "#ffffff",
        "primary_text": "#1a1a1a",
        "secondary_text": "#666666",
        "muted_text": "#888888",
        "badge_text": "#888888",
        "border": "rgba(0, 0, 0, 0.08)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
    "classic": {
        "window_bg": "#0d0d0d",
        "panel_bg": "#181818",
        "card_bg": "#181818",
        "primary_text": "#e0e0e0",
        "secondary_text": "#999999",
        "muted_text": "#bbbbbb",
        "badge_text": "#bbbbbb",
        "border": "rgba(255, 255, 255, 0.06)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
}


class Theme:
    """Manages the active color palette and applies it to widgets."""

    def __init__(self, preset: ThemePreset = ThemePreset.DARK) -> None:
        """Initialize with the given preset.

        Args:
            preset: The initial theme preset. Defaults to DARK.
        """
        self._preset = preset

    def current_id(self) -> str:
        """Return the identifier of the active preset.

        Returns:
            The preset value string, e.g. "dark".
        """
        return self._preset.value

    def current(self) -> dict[str, str]:
        """Return the active color palette dictionary.

        Returns:
            Mapping of color role names to color values.
        """
        return PALETTES[self.current_id()]

    def set_preset(self, preset: ThemePreset) -> None:
        """Switch to a different preset.

        Args:
            preset: The new theme preset to activate.
        """
        self._preset = preset

    def apply_to_widget(self, widget: QWidget) -> None:
        """Apply the current palette to a widget via styleSheet.

        Args:
            widget: The widget to style.
        """
        palette = self.current()
        widget.setStyleSheet(
            f"background-color: {palette['panel_bg']};"
            f" color: {palette['primary_text']};"
        )
