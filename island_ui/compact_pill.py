from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class CompactPill(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._count = 0
        self._agents: list[str] = []
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 8, 16, 8)
        self._layout.setSpacing(8)

        self._count_label = QLabel("0 requests")
        self._count_label.setStyleSheet("font-size: 13px; color: #eeeeee; font-weight: 500;")
        self._layout.addWidget(self._count_label)

        self._agents_label = QLabel("")
        self._agents_label.setStyleSheet("font-size: 11px; color: #888888;")
        self._layout.addWidget(self._agents_label)

        self._layout.addStretch()

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            CompactPill {
                background-color: #1e1e23;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        self.setMinimumWidth(180)
        self.setMaximumWidth(400)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_count(self, count: int, active: int = 0) -> None:
        self._count = count
        if count > 0:
            text = f"{count} waiting"
        elif active > 0:
            text = f"{active} active"
        else:
            text = "AI Island"
        self._count_label.setText(text)
        # 真实模式下始终显示 pill，让用户知道 AI Island 在运行

    def set_agents(self, agents: list[str]) -> None:
        self._agents = agents
        if agents:
            self._agents_label.setText("  ·  " + ", ".join(agents))
        else:
            self._agents_label.setText("")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
