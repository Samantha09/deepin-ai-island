from PySide6.QtWidgets import QLabel

from island_ui.cards.base_card import EventCard
from island_ui.events import Event, ProgressUpdated, SessionStarted, SessionEnded, ChatMessage


class MessageCard(EventCard):
    """纯文本消息卡片，用于展示最近几条聊天/事件记录。"""

    def __init__(self, event: Event, parent=None):
        super().__init__(event, parent)
        self._colors: dict[str, str] = {}
        text = self._extract_text(event)
        if not text:
            text = event.type

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        # 限制最大高度，约 3 行文本
        self._label.setMaximumHeight(56)
        self._layout.addWidget(self._label)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色."""
        self._colors = colors
        super().refresh_theme(colors)
        secondary = colors.get("secondary_text", "#cccccc")
        self._label.setStyleSheet(f"font-size: 12px; color: {secondary};")

    @staticmethod
    def _extract_text(event: Event) -> str:
        if isinstance(event, ChatMessage):
            role = event.payload.get("role", "assistant")
            content = event.payload.get("content", "")
            prefix = "用户" if role == "user" else ("AI" if role == "assistant" else "系统")
            return f"{prefix}: {content}"
        if isinstance(event, ProgressUpdated):
            return event.message
        if isinstance(event, SessionStarted):
            return event.payload.get("task", "Session started")
        if isinstance(event, SessionEnded):
            return "Session completed"
        return event.payload.get("message", "")
