"""固定宽度的文本图标占位标签."""

from PySide6.QtWidgets import QLabel


class IconLabel(QLabel):
    """16px 等宽图标占位, 12px 字体."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setFixedWidth(16)
        self.setStyleSheet("font-size: 12px;")
