"""Settings drawer widget bound to ConfigManager."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        self._title = QLabel("Settings")
        header.addWidget(self._title)
        header.addStretch()
        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.clicked.connect(self.closed.emit)
        header.addWidget(self._close_btn)
        root.addLayout(header)

        self.refresh_theme({
            "panel_bg": "#1e1e23",
            "control_bg": "#2a2a30",
            "control_border": "#3a3a40",
            "primary_text": "#e0e0e0",
            "selection_bg": "#4a4a50",
            "accent": "#4a90d9",
            "label_text": "#c0c0c0",
            "title_text": "#ffffff",
            "hover_bg": "#3a3a40",
        })

        root.addWidget(self._separator())

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "classic"])
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        root.addLayout(self._row("Theme", self._theme_combo))
        root.addWidget(self._separator())

        # Animation
        self._anim_check = QCheckBox()
        self._anim_check.stateChanged.connect(self._on_anim_changed)
        root.addLayout(self._row("Animation", self._anim_check))
        root.addWidget(self._separator())

        # Compact timeout
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1000, 30000)
        self._timeout_spin.setSingleStep(500)
        self._timeout_spin.setSuffix(" ms")
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        root.addLayout(self._row("Compact timeout", self._timeout_spin))
        root.addWidget(self._separator())

        # Position X
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-500, 500)
        self._pos_x_spin.valueChanged.connect(self._on_pos_x_changed)
        root.addLayout(self._row("Position X", self._pos_x_spin))
        root.addWidget(self._separator())

        # Position Y
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-200, 200)
        self._pos_y_spin.valueChanged.connect(self._on_pos_y_changed)
        root.addLayout(self._row("Position Y", self._pos_y_spin))
        root.addWidget(self._separator())

        # Reset button
        self._reset_button = QPushButton("Reset defaults")
        self._reset_button.clicked.connect(self._on_reset)
        root.addWidget(self._reset_button)

        root.addStretch()

        self._load_from_config()

    def _separator(self) -> QWidget:
        """Return a 1px horizontal separator line."""
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.06);")
        return line

    def _row(self, label_text: str, control: QWidget) -> QHBoxLayout:
        """Create a settings row with a fixed-width label and a control."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        label = QLabel(label_text)
        label.setFixedWidth(120)
        layout.addWidget(label)
        layout.addWidget(control, 1)
        return layout

    def _on_theme_changed(self, text: str) -> None:
        """Persist theme selection."""
        self._config.set("theme.id", text)
        self._config.save()

    def _on_anim_changed(self, state: int) -> None:
        """Persist animation toggle."""
        self._config.set("island.animation_enabled", bool(state))
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
            f"  border: 1px solid {colors['control_border']};"
            f"  border-radius: 6px;"
            f"  padding: 4px 8px;"
            f"  min-height: 24px;"
            f"}}"
            f"QComboBox::drop-down {{"
            f"  border: none;"
            f"  width: 20px;"
            f"}}"
            f"QComboBox QAbstractItemView {{"
            f"  background-color: {colors['control_bg']};"
            f"  color: {colors['primary_text']};"
            f"  selection-background-color: {colors['selection_bg']};"
            f"}}"
            f"QCheckBox {{"
            f"  color: {colors['primary_text']};"
            f"  spacing: 8px;"
            f"}}"
            f"QCheckBox::indicator {{"
            f"  width: 18px;"
            f"  height: 18px;"
            f"  border-radius: 4px;"
            f"  border: 1px solid {colors['control_border']};"
            f"  background-color: {colors['control_bg']};"
            f"}}"
            f"QCheckBox::indicator:checked {{"
            f"  background-color: {colors['accent']};"
            f"  border: 1px solid {colors['accent']};"
            f"}}"
            f"QPushButton {{"
            f"  background-color: {colors['control_bg']};"
            f"  color: {colors['primary_text']};"
            f"  border: 1px solid {colors['control_border']};"
            f"  border-radius: 6px;"
            f"  padding: 6px 12px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {colors['hover_bg']};"
            f"}}"
            f"QLabel {{"
            f"  color: {colors['label_text']};"
            f"}}"
        )
        self._title.setStyleSheet(
            f"color: {colors['title_text']}; font-size: 16px; font-weight: bold;"
        )
        self._close_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {colors['label_text']};"
            f"  border: none;"
            f"  font-size: 18px;"
            f"  font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"  color: {colors['title_text']};"
            f"}}"
        )

    def _load_from_config(self) -> None:
        """Sync widget states from ConfigManager."""
        theme = self._config.get("theme.id", "dark")
        index = self._theme_combo.findText(theme)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)

        self._anim_check.setChecked(
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
