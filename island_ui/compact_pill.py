from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class CompactPill(QFrame):
    clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._count = 0
        self._agents: list[str] = []
        self._setup_ui()
        self._colors: dict[str, str] = {}

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 8, 16, 8)
        self._layout.setSpacing(8)

        # Pending permission indicator (amber dot)
        self._pending_indicator = QLabel("●")
        self._pending_indicator.setStyleSheet("font-size: 10px;")
        self._pending_indicator.setVisible(False)
        self._layout.addWidget(self._pending_indicator)

        self._count_label = QLabel("0 requests")
        self._count_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        self._layout.addWidget(self._count_label)

        self._agents_label = QLabel("")
        self._agents_label.setStyleSheet("font-size: 11px;")
        self._layout.addWidget(self._agents_label)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                font-size: 14px;
                border: none;
                padding: 0 4px;
            }
        """)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        self._layout.addWidget(self._settings_btn)

        self._layout.addStretch()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """Apply theme colors to pill and child widgets."""
        self._colors = colors
        self.setStyleSheet(f"""
            CompactPill {{
                background-color: {colors['panel_bg']};
                border-radius: 20px;
                border: 1px solid {colors['border']};
            }}
        """)
        self._pending_indicator.setStyleSheet(
            f"color: {colors['accent_amber']}; font-size: 10px;"
        )
        self._count_label.setStyleSheet(
            f"font-size: 13px; color: {colors['primary_text']}; font-weight: 500;"
        )
        self._agents_label.setStyleSheet(
            f"font-size: 11px; color: {colors['secondary_text']};"
        )
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {colors['secondary_text']};
                font-size: 14px;
                border: none;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                color: {colors['primary_text']};
            }}
        """)

    def _setup_style(self) -> None:
        self.setMinimumWidth(180)
        self.setMaximumWidth(400)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_count(self, waiting: int, active: int, total: int, waiting_label: str = "") -> None:
        self._count = waiting
        if waiting > 0 and waiting_label:
            text = f"{waiting} waiting / {total} total — {waiting_label}"
        elif waiting > 0:
            text = f"{waiting} waiting / {total} total"
        elif total > 0:
            text = f"{total} sessions"
        else:
            text = "AI Island"
        self._count_label.setText(text)
        self._pending_indicator.setVisible(waiting > 0)
        self.setVisible(total > 0)

    def set_agents(self, agents: list[str]) -> None:
        self._agents = agents
        if agents:
            self._agents_label.setText("  ·  " + ", ".join(agents))
        else:
            self._agents_label.setText("")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
