from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QWidget,
)


class CompactPill(QFrame):
    """Dynamic Island collapsed state: minimal notch content."""

    clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._count = 0
        self._agents: list[str] = []
        self._colors: dict[str, str] = {}
        self._waiting_label = ""
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 6, 14, 6)
        self._layout.setSpacing(6)

        # Status dot (colored circle, no shadow for performance)
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("font-size: 6px; color: #CAFF00;")
        self._status_dot.setFixedSize(10, 10)
        self._layout.addWidget(self._status_dot)

        # Spacer in the middle
        self._layout.addStretch()

        # Count label on the right
        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #FFFFFF;"
        )
        self._layout.addWidget(self._count_label)

        # Settings gear
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

    def _setup_style(self) -> None:
        self.setFixedHeight(32)
        self.setMinimumWidth(80)
        self.setMaximumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        bg = colors.get("panel_bg", "#000000")
        primary = colors.get("primary_text", "#ffffff")
        secondary = colors.get("secondary_text", "#8e8e93")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border: none;
            }}
            QFrame:hover {{
                background-color: {colors.get("card_bg_hover", "#1A1A1A")};
            }}
        """)
        self._count_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {primary};"
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
        self._waiting_label = waiting_label
        self.setVisible(total > 0)

        # Status dot color
        if waiting > 0:
            color = self._colors.get("accent_amber", "#F59E0B")
        elif active > 0:
            color = self._colors.get("accent_blue", "#66E8F8")
        else:
            color = self._colors.get("accent_idle", "#CAFF00")

        self._status_dot.setStyleSheet(f"font-size: 6px; color: {color};")

        # Update count label
        self._count_label.setText(str(total))

    def set_agents(self, agents: list[str]) -> None:
        self._agents = agents

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
