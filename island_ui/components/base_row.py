"""可 hover 的圆角行容器基类."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout


class BaseRow(QFrame):
    """带 hover 高亮的圆角行容器.

    默认背景透明, 鼠标悬停时变为 theme 的 card_bg_hover.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hovered = False
        self._colors: dict[str, str] = {}

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(10)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色并刷新样式."""
        self._colors = colors
        self._update_style()

    def _update_style(self) -> None:
        bg = self._colors.get("card_bg_hover", "rgba(255,255,255,0.08)") if self._hovered else "transparent"
        radius = "8px"
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {bg};"
            f"  border-radius: {radius};"
            f"}}"
        )
