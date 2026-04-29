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

        self.setStyleSheet(
            "SettingsDrawer {"
            "  background-color: #1e1e23;"
            "  border-radius: 16px;"
            "}"
            "QComboBox, QSpinBox {"
            "  background-color: #2a2a30;"
            "  color: #e0e0e0;"
            "  border: 1px solid #3a3a40;"
            "  border-radius: 6px;"
            "  padding: 4px 8px;"
            "  min-height: 24px;"
            "}"
            "QComboBox::drop-down {"
            "  border: none;"
            "  width: 20px;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background-color: #2a2a30;"
            "  color: #e0e0e0;"
            "  selection-background-color: #4a4a50;"
            "}"
            "QCheckBox {"
            "  color: #e0e0e0;"
            "  spacing: 8px;"
            "}"
            "QCheckBox::indicator {"
            "  width: 18px;"
            "  height: 18px;"
            "  border-radius: 4px;"
            "  border: 1px solid #3a3a40;"
            "  background-color: #2a2a30;"
            "}"
            "QCheckBox::indicator:checked {"
            "  background-color: #4a90d9;"
            "  border: 1px solid #4a90d9;"
            "}"
            "QPushButton {"
            "  background-color: #2a2a30;"
            "  color: #e0e0e0;"
            "  border: 1px solid #3a3a40;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #3a3a40;"
            "}"
            "QLabel {"
            "  color: #c0c0c0;"
            "}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Settings")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: transparent;"
            "  color: #c0c0c0;"
            "  border: none;"
            "  font-size: 18px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  color: #ffffff;"
            "}"
        )
        close_btn.clicked.connect(self.closed.emit)
        header.addWidget(close_btn)
        root.addLayout(header)

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
