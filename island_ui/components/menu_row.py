"""菜单行: 图标 + 标签 + 右侧控件."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from island_ui.components.base_row import BaseRow
from island_ui.components.icon_label import IconLabel


class MenuRow(BaseRow):
    """设置抽屉中的标准行.

    左侧可选图标, 中间标签, 右侧任意控件.
    """

    def __init__(self, label: str, icon: str = "", control: QWidget | None = None, parent=None) -> None:
        super().__init__(parent)
        self._label_text = label

        if icon:
            self._icon = IconLabel(icon)
            self._layout.addWidget(self._icon)
        else:
            self._icon = None
            # 无图标时左侧留白保持对齐
            spacer = QLabel("")
            spacer.setFixedWidth(16)
            self._layout.addWidget(spacer)

        self._label = QLabel(label)
        self._label.setStyleSheet("font-size: 13px; font-weight: 500;")
        self._layout.addWidget(self._label)

        self._layout.addStretch()

        if control:
            self._control = control
            self._layout.addWidget(control)
        else:
            self._control = None

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
