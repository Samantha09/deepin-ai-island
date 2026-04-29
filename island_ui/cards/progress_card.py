from PySide6.QtWidgets import QVBoxLayout, QLabel, QProgressBar, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.events import ProgressUpdated


class ProgressCard(EventCard):
    def __init__(self, event: ProgressUpdated, parent: QWidget = None):
        super().__init__(event, parent)
        self._colors: dict[str, str] = {}
        message = event.payload.get("message", "")
        percent = event.payload.get("percent")

        self.set_content("Progress", message)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._layout.addWidget(self._progress)

        self._percent_label = QLabel("")
        self._layout.addWidget(self._percent_label)
        self._set_percent(percent)

    def _set_percent(self, percent: int | None) -> None:
        if percent is not None:
            self._progress.setValue(percent)
            self._percent_label.setText(f"{percent}%")
        else:
            self._progress.setRange(0, 0)  # indeterminate

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色."""
        self._colors = colors
        super().refresh_theme(colors)
        accent = colors.get("accent_blue", "#2196F3")
        control_bg = colors.get("control_bg", "rgba(255,255,255,0.08)")
        muted = colors.get("muted_text", "#888888")
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {control_bg};
                border-radius: 4px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 4px;
            }}
        """)
        self._percent_label.setStyleSheet(f"font-size: 11px; color: {muted};")
