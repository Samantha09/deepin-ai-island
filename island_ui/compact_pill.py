from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QWidget, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor


class CompactPill(QFrame):
    """Dynamic Island collapsed state: MioIsland-style compact notch content."""

    clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._count = 0
        self._agents: list[str] = []
        self._colors: dict[str, str] = {}
        self._waiting_label = ""
        self._slide_index = 0
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(10, 4, 10, 4)
        self._layout.setSpacing(6)

        # Status dot with shadow (6px)
        self._status_dot = QLabel("")
        self._status_dot.setFixedSize(6, 6)
        self._status_dot.setStyleSheet("background: transparent;")
        self._status_dot_shadow = QGraphicsDropShadowEffect(self._status_dot)
        self._status_dot_shadow.setBlurRadius(3)
        self._status_dot_shadow.setColor(QColor(0, 0, 0, 128))
        self._status_dot_shadow.setOffset(0, 0)
        self._status_dot.setGraphicsEffect(self._status_dot_shadow)
        self._layout.addWidget(self._status_dot)

        # Buddy icon (small avatar/indicator)
        self._buddy_icon = QLabel("◉")
        self._buddy_icon.setStyleSheet("font-size: 10px; color: #9A9A9A;")
        self._buddy_icon.setFixedSize(16, 16)
        self._layout.addWidget(self._buddy_icon)

        # Carousel text label (monospaced 13pt medium)
        self._carousel_label = QLabel("")
        self._carousel_label.setStyleSheet(
            "font-size: 13px; font-weight: 500; font-family: 'DejaVu Sans Mono', 'Noto Mono', monospace;"
        )
        self._layout.addWidget(self._carousel_label)

        self._layout.addStretch()

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

        # Carousel timer: switch every 3 seconds
        self._carousel_timer = QTimer(self)
        self._carousel_timer.setInterval(3000)
        self._carousel_timer.timeout.connect(self._rotate_carousel)

        # Pulse timer for status dot (simpler than QPropertyAnimation on QSize)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(600)
        self._pulse_timer.timeout.connect(self._toggle_pulse)
        self._pulse_state = False

    def _setup_style(self) -> None:
        self.setFixedHeight(38)
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

        hover_bg = colors.get("card_bg_hover", "#2A2A2A")
        card_border = colors.get("card_border", "#2A2A2A")
        card_border_hover = colors.get("card_border_hover", "#3A3A3A")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border: 1px solid {card_border};
            }}
            QFrame:hover {{
                background-color: {hover_bg};
                border: 1px solid {card_border_hover};
            }}
        """)
        self._carousel_label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {primary};"
            f"font-family: 'DejaVu Sans Mono', 'Noto Mono', monospace;"
        )
        self._buddy_icon.setStyleSheet(f"font-size: 10px; color: {secondary};")
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

        # Update status dot color based on state
        if waiting > 0:
            color = self._colors.get("accent_amber", "#F59E0B")
            self._status_dot_shadow.setColor(QColor(color))
            # Start pulse when attention needed
            self._pulse_timer.start()
        elif active > 0:
            color = self._colors.get("accent_blue", "#66E8F8")
            self._status_dot_shadow.setColor(QColor(color))
            self._pulse_timer.stop()
            self._status_dot.setFixedSize(6, 6)
        else:
            color = self._colors.get("accent_idle", "#CAFF00")
            self._status_dot_shadow.setColor(QColor(color))
            self._pulse_timer.stop()
            self._status_dot.setFixedSize(6, 6)

        # Build carousel slides
        self._slides = []
        if waiting > 0 and waiting_label:
            self._slides.append(f"需要批准: {waiting_label}")
        if self._agents:
            self._slides.append(f"Agent: {', '.join(self._agents)}")
        if total > 0:
            self._slides.append(f"会话: {total}")
        if waiting > 0:
            self._slides.append(f"等待: {waiting}")
        if not self._slides:
            self._slides.append("AI Island")

        self._slide_index = 0
        self._update_carousel()

        # Start carousel timer
        if total > 0 and len(self._slides) > 1:
            self._carousel_timer.start()
        else:
            self._carousel_timer.stop()

    def set_agents(self, agents: list[str]) -> None:
        self._agents = agents

    def _rotate_carousel(self) -> None:
        if not self._slides:
            return
        self._slide_index = (self._slide_index + 1) % len(self._slides)
        self._update_carousel()

    def _toggle_pulse(self) -> None:
        self._pulse_state = not self._pulse_state
        size = 8 if self._pulse_state else 5
        self._status_dot.setFixedSize(size, size)

    def _update_carousel(self) -> None:
        if self._slides:
            text = self._slides[self._slide_index]
            # Truncate if too long
            if len(text) > 28:
                text = text[:25] + "..."
            self._carousel_label.setText(text)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
