"""开关行: 图标 + 标签 + 状态指示点 + On/Off 文字."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from island_ui.components.base_row import BaseRow
from island_ui.components.icon_label import IconLabel


class ToggleRow(BaseRow):
    """可点击的开关设置行.

    点击整行切换状态, 右侧显示绿色/灰色指示点和 On/Off 标签.
    """

    toggled = Signal(bool)

    def __init__(self, label: str, icon: str = "", initial: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._label_text = label
        self._is_on = initial

        if icon:
            self._icon = IconLabel(icon)
            self._layout.addWidget(self._icon)
        else:
            self._icon = None
            spacer = QLabel("")
            spacer.setFixedWidth(16)
            self._layout.addWidget(spacer)

        self._label = QLabel(label)
        self._label.setStyleSheet("font-size: 13px; font-weight: 500;")
        self._layout.addWidget(self._label)

        self._layout.addStretch()

        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 6px;")
        self._layout.addWidget(self._dot)

        self._status = QLabel("On" if initial else "Off")
        self._status.setStyleSheet("font-size: 11px;")
        self._layout.addWidget(self._status)

        self.mousePressEvent = self._on_click  # type: ignore[method-assign]

    def _on_click(self, event) -> None:  # noqa: ARG002
        self._is_on = not self._is_on
        self._update_state()
        self.toggled.emit(self._is_on)

    def _update_state(self) -> None:
        self._status.setText("On" if self._is_on else "Off")
        self._apply_dot_color()

    def _apply_dot_color(self) -> None:
        green = self._colors.get("accent_green", "#66bf73")
        muted = self._colors.get("muted_text", "rgba(255,255,255,0.4)")
        color = green if self._is_on else muted
        self._dot.setStyleSheet(f"font-size: 6px; color: {color};")

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色."""
        super().refresh_theme(colors)
        text_color = colors.get("primary_text", "#eeeeee")
        muted = colors.get("muted_text", "rgba(255,255,255,0.4)")
        self._label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {text_color};"
        )
        if self._icon:
            self._icon.setStyleSheet(f"font-size: 12px; color: {muted};")
        self._status.setStyleSheet(f"font-size: 11px; color: {muted};")
        self._apply_dot_color()

    def is_on(self) -> bool:
        """返回当前开关状态."""
        return self._is_on

    def set_on(self, value: bool) -> None:
        """设置开关状态(不发射信号)."""
        if self._is_on != value:
            self._is_on = value
            self._update_state()
