"""Settings drawer widget bound to ConfigManager."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from island_ui.components import MenuDivider, MenuRow, ToggleRow
from island_ui.config_manager import ConfigManager

__all__ = ["SettingsDrawer"]


class SettingsDrawer(QWidget):
    """Slide-out settings panel with live ConfigManager binding."""

    closed = Signal()

    def __init__(self, config: ConfigManager, parent: QWidget | None = None) -> None:
        """Initialize the drawer.

        Args:
            config: ConfigManager instance to bind to.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        # Back row (closes drawer)
        self._back_row = MenuRow("Back", icon="←")
        self._back_row.mousePressEvent = lambda e: self.closed.emit()  # type: ignore[method-assign]
        root.addWidget(self._back_row)

        root.addWidget(MenuDivider())

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "classic"])
        self._theme_combo.setFixedWidth(100)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self._theme_row = MenuRow("Theme", control=self._theme_combo)
        root.addWidget(self._theme_row)

        root.addWidget(MenuDivider())

        # Animation toggle
        self._anim_row = ToggleRow("Animation", icon="✦", initial=True)
        self._anim_row.toggled.connect(self._on_anim_changed)
        root.addWidget(self._anim_row)

        root.addWidget(MenuDivider())

        # Compact timeout
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1000, 30000)
        self._timeout_spin.setSingleStep(500)
        self._timeout_spin.setSuffix(" ms")
        self._timeout_spin.setFixedWidth(100)
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        self._timeout_row = MenuRow("Compact timeout", control=self._timeout_spin)
        root.addWidget(self._timeout_row)

        root.addWidget(MenuDivider())

        # Position X
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-500, 500)
        self._pos_x_spin.setFixedWidth(80)
        self._pos_x_spin.valueChanged.connect(self._on_pos_x_changed)
        self._pos_x_row = MenuRow("Position X", control=self._pos_x_spin)
        root.addWidget(self._pos_x_row)

        root.addWidget(MenuDivider())

        # Position Y
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-200, 200)
        self._pos_y_spin.setFixedWidth(80)
        self._pos_y_spin.valueChanged.connect(self._on_pos_y_changed)
        self._pos_y_row = MenuRow("Position Y", control=self._pos_y_spin)
        root.addWidget(self._pos_y_row)

        root.addWidget(MenuDivider())

        # Reset defaults
        self._reset_row = MenuRow("Reset defaults", icon="↺")
        self._reset_row.mousePressEvent = lambda e: self._on_reset()  # type: ignore[method-assign]
        root.addWidget(self._reset_row)

        root.addStretch()

        self._load_from_config()

    def _on_theme_changed(self, text: str) -> None:
        """Persist theme selection."""
        self._config.set("theme.id", text)
        self._config.save()

    def _on_anim_changed(self, state: bool) -> None:
        """Persist animation toggle."""
        self._config.set("island.animation_enabled", state)
        self._config.save()

    def _on_timeout_changed(self, value: int) -> None:
        """Persist compact timeout."""
        self._config.set("island.compact_timeout_ms", value)
        self._config.save()

    def _on_pos_x_changed(self, value: int) -> None:
        """Persist X position offset."""
        self._config.set("island.position_offset_x", value)
        self._config.save()

    def _on_pos_y_changed(self, value: int) -> None:
        """Persist Y position offset."""
        self._config.set("island.position_offset_y", value)
        self._config.save()

    def _on_reset(self) -> None:
        """Reset configuration to defaults and refresh UI."""
        self._config.reset_to_defaults()
        self._config.save()
        self._load_from_config()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """Apply theme colors to the drawer and its controls."""
        self.setStyleSheet(
            f"SettingsDrawer {{"
            f"  background-color: {colors['panel_bg']};"
            f"  border-radius: 16px;"
            f"}}"
            f"QComboBox, QSpinBox {{"
            f"  background-color: {colors['control_bg']};"
            f"  color: {colors['primary_text']};"
            f"  border: 1px solid {colors['border']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 8px;"
            f"  min-height: 24px;"
            f"  font-size: 12px;"
            f"}}"
            f"QComboBox::drop-down {{"
            f"  border: none;"
            f"  width: 20px;"
            f"}}"
            f"QComboBox QAbstractItemView {{"
            f"  background-color: {colors['control_bg']};"
            f"  color: {colors['primary_text']};"
            f"  selection-background-color: {colors['card_bg_hover']};"
            f"}}"
        )
        self._back_row.refresh_theme(colors)
        self._theme_row.refresh_theme(colors)
        self._anim_row.refresh_theme(colors)
        self._timeout_row.refresh_theme(colors)
        self._pos_x_row.refresh_theme(colors)
        self._pos_y_row.refresh_theme(colors)
        self._reset_row.refresh_theme(colors)
        for child in self.findChildren(MenuDivider):
            child.refresh_theme(colors)

    def _load_from_config(self) -> None:
        """Sync widget states from ConfigManager."""
        theme = self._config.get("theme.id", "dark")
        index = self._theme_combo.findText(theme)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)

        self._anim_row.set_on(
            self._config.get("island.animation_enabled", True)
        )
        self._timeout_spin.setValue(
            self._config.get("island.compact_timeout_ms", 5000)
        )
        self._pos_x_spin.setValue(
            self._config.get("island.position_offset_x", 0)
        )
        self._pos_y_spin.setValue(
            self._config.get("island.position_offset_y", 0)
        )
