"""菜单分隔线组件."""

from PySide6.QtWidgets import QWidget


class MenuDivider(QWidget):
    """1px 水平分隔线, 上下 4px margin."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(9)  # 1px line + 4px top/bottom margin
        self._color = "rgba(255,255,255,0.08)"

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """更新分隔线颜色."""
        self._color = colors.get("divider", "rgba(255,255,255,0.08)")
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"MenuDivider {{"
            f"  background-color: transparent;"
            f"  border: none;"
            f"}}"
            f"MenuDivider::after {{"
            f"  content: '';"
            f"  display: block;"
            f"  margin-top: 4px;"
            f"  height: 1px;"
            f"  background-color: {self._color};"
            f"}}"
        )
