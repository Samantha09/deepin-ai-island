from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget

from island_ui.animations import FadeSlideInAnimation, FadeSlideOutAnimation
from island_ui.events import Event


class EventCard(QFrame):
    resolved = Signal(object)  # emits the card instance

    def __init__(self, event: Event, parent: QWidget = None):
        super().__init__(parent)
        self._event = event
        self._resolved = False
        self._setup_style()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(8)

        self._enter_anim = FadeSlideInAnimation(self, duration_ms=250)

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            EventCard {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 14px;
                border: none;
            }
        """)
        self.setMinimumWidth(320)

    def set_content(self, title: str, body: str) -> None:
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; color: #888888;")
        self._layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setStyleSheet("font-size: 13px; color: #eeeeee;")
        body_label.setWordWrap(True)
        self._layout.addWidget(body_label)

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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._enter_anim.start()
