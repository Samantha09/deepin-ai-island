from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class CompactPill(QFrame):
    """Dynamic Island collapsed state: compact black pill."""

    clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._count = 0
        self._agents: list[str] = []
        self._colors: dict[str, str] = {}
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 6, 14, 6)
        self._layout.setSpacing(6)

        # Amber dot indicator
        self._pending_indicator = QLabel("●")
        self._pending_indicator.setStyleSheet("font-size: 8px;")
        self._pending_indicator.setVisible(False)
        self._layout.addWidget(self._pending_indicator)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        self._layout.addWidget(self._count_label)

        self._agents_label = QLabel("")
        self._agents_label.setStyleSheet("font-size: 11px;")
        self._layout.addWidget(self._agents_label)

        # Settings gear (small, subtle)
        self._settings_btn = QPushButton("⋯")
        self._settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                padding: 0 0 0 4px;
                color: #8e8e93;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        self._layout.addWidget(self._settings_btn)

        self._layout.addStretch()

    def _setup_style(self) -> None:
        self.setFixedHeight(32)
        self.setMinimumWidth(120)
        self.setMaximumWidth(320)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """Apply theme colors to pill and child widgets."""
        self._colors = colors
        bg = colors.get("panel_bg", "#000000")
        primary = colors.get("primary_text", "#ffffff")
        secondary = colors.get("secondary_text", "#8e8e93")
        amber = colors.get("accent_amber", "#ff9500")

        hover_bg = colors.get("card_bg_hover", "#2c2c2e")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: 16px;
                border: none;
            }}
            QFrame:hover {{
                background-color: {hover_bg};
            }}
        """)
        self._pending_indicator.setStyleSheet(
            f"color: {amber}; font-size: 8px;"
        )
        self._count_label.setStyleSheet(
            f"font-size: 12px; color: {primary}; font-weight: 600;"
        )
        self._agents_label.setStyleSheet(
            f"font-size: 11px; color: {secondary};"
        )
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                padding: 0 0 0 4px;
                color: {secondary};
            }}
            QPushButton:hover {{
                color: {primary};
            }}
        """)

    def set_count(self, waiting: int, active: int, total: int, waiting_label: str = "") -> None:
        self._count = waiting
        if waiting > 0 and waiting_label:
            text = f"{waiting}"
        elif waiting > 0:
            text = f"{waiting}"
        elif total > 0:
            text = f"{total}"
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
