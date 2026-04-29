"""菜单分隔线组件."""

from PySide6.QtWidgets import QWidget


class MenuDivider(QWidget):
    """1px 水平分隔线, 上下 4px margin."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(9)  # 1px line + 4px top/bottom margin
        self._color = "rgba(255,255,255,0.08)"
        self._line = QWidget(self)
        self._line.setFixedHeight(1)
        self._update_style()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """更新分隔线颜色."""
        self._color = colors.get("divider", "rgba(255,255,255,0.08)")
        self._update_style()

    def _update_style(self) -> None:
        self._line.setStyleSheet(
            f"background-color: {self._color}; border: none;"
        )

    def resizeEvent(self, event) -> None:
        """居中放置 1px 分隔线."""
        super().resizeEvent(event)
        self._line.setGeometry(0, 4, self.width(), 1)
