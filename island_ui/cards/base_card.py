from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QSizePolicy

from island_ui.animations import FadeSlideInAnimation, FadeSlideOutAnimation
from island_ui.events import Event


class EventCard(QFrame):
    resolved = Signal(object)  # emits the card instance

    def __init__(self, event: Event, parent: QWidget = None):
        super().__init__(parent)
        self._event = event
        self._resolved = False
        self._colors: dict[str, str] = {}
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._setup_style()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(8)

        self._enter_anim = FadeSlideInAnimation(self, duration_ms=250)

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border-radius: 16px;
                border: 1px solid #2A2A2A;
            }
        """)
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_content(self, title: str, body: str) -> None:
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-size: 11px; color: #9A9A9A;")
        self._layout.addWidget(self._title_label)

        self._body_label = QLabel(body)
        self._body_label.setStyleSheet("font-size: 13px; color: #FFFFFF;")
        self._body_label.setWordWrap(True)
        self._layout.addWidget(self._body_label)

    def event_data(self) -> Event:
        return self._event

    def is_resolved(self) -> bool:
        return self._resolved

    def mark_resolved(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.setEnabled(False)
        self._exit_anim = FadeSlideOutAnimation(self, duration_ms=250)
        self._exit_anim.start()
        # Schedule deletion after animation finishes
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self.deleteLater)
        self.resolved.emit(self)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """Apply theme colors to card."""
        self._colors = colors
        card_border = colors.get("card_border", "#2A2A2A")
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {colors['card_bg']};"
            f"  border-radius: 16px;"
            f"  border: 1px solid {card_border};"
            f"}}"
        )
        if hasattr(self, "_title_label"):
            self._title_label.setStyleSheet(
                f"font-size: 11px; color: {colors['secondary_text']};"
            )
        if hasattr(self, "_body_label"):
            self._body_label.setStyleSheet(
                f"font-size: 13px; color: {colors['primary_text']};"
            )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._enter_anim.start()
