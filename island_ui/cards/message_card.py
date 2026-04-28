from PySide6.QtWidgets import QLabel

from island_ui.cards.base_card import EventCard
from island_ui.events import Event, ProgressUpdated, SessionStarted, SessionEnded


class MessageCard(EventCard):
    """纯文本消息卡片，用于展示最近几条聊天/事件记录。"""

    def __init__(self, event: Event, parent=None):
        super().__init__(event, parent)
        text = self._extract_text(event)
        if not text:
            text = event.type

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 12px; color: #cccccc;")
        # 限制最大高度，约 3 行文本
        label.setMaximumHeight(56)
        self._layout.addWidget(label)

    @staticmethod
    def _extract_text(event: Event) -> str:
        if isinstance(event, ProgressUpdated):
            return event.message
        if isinstance(event, SessionStarted):
            return event.payload.get("task", "Session started")
        if isinstance(event, SessionEnded):
            return "Session completed"
        return event.payload.get("message", "")
