from PySide6.QtWidgets import QVBoxLayout, QLabel, QProgressBar, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.events import ProgressUpdated


class ProgressCard(EventCard):
    def __init__(self, event: ProgressUpdated, parent: QWidget = None):
        super().__init__(event, parent)
        message = event.payload.get("message", "")
        percent = event.payload.get("percent")

        self.set_content("Progress", message)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 4px;
            }
        """)
        if percent is not None:
            self._progress.setValue(percent)
        else:
            self._progress.setRange(0, 0)  # indeterminate

        self._layout.addWidget(self._progress)

        self._percent_label = QLabel("")
        self._percent_label.setStyleSheet("font-size: 11px; color: #888888;")
        if percent is not None:
            self._percent_label.setText(f"{percent}%")
        self._layout.addWidget(self._percent_label)
