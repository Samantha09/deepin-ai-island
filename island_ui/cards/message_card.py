from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.events import Event, ProgressUpdated, SessionStarted, SessionEnded, ChatMessage


class MessageCard(EventCard):
    """聊天消息卡片：用户消息气泡 + 助手消息带指示点."""

    def __init__(self, event: Event, parent=None):
        super().__init__(event, parent)
        self._colors: dict[str, str] = {}
        self._role = ""
        self._setup_content(event)

    def _setup_content(self, event: Event) -> None:
        if isinstance(event, ChatMessage):
            self._role = event.payload.get("role", "assistant")
            content = event.payload.get("content", "")
            if self._role == "user":
                self._setup_user_bubble(content)
            else:
                self._setup_assistant_message(content)
        else:
            text = self._extract_text(event)
            if not text:
                text = event.type
            self._label = QLabel(text)
            self._label.setWordWrap(True)
            self._label.setMaximumHeight(56)
            self._layout.addWidget(self._label)

    def _setup_user_bubble(self, content: str) -> None:
        """用户消息：18px 圆角气泡，#2F2F2F 背景."""
        self._label = QLabel(content)
        self._label.setWordWrap(True)
        self._label.setMaximumHeight(120)
        self._label.setStyleSheet("""
            font-size: 13px;
            color: #FFFFFF;
            background-color: #2F2F2F;
            border-radius: 18px;
            padding: 10px 14px;
        """)
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # 右对齐容器
        wrapper = QWidget()
        h_layout = QHBoxLayout(wrapper)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addStretch()
        h_layout.addWidget(self._label)
        self._layout.addWidget(wrapper)

    def _setup_assistant_message(self, content: str) -> None:
        """助手消息：6px 点指示器 + 文本."""
        wrapper = QWidget()
        h_layout = QHBoxLayout(wrapper)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        # 6px 指示点
        self._dot = QLabel("●")
        self._dot.setFixedSize(6, 6)
        self._dot.setStyleSheet("font-size: 6px; color: #FFFFFF;")
        h_layout.addWidget(self._dot)

        self._label = QLabel(content)
        self._label.setWordWrap(True)
        self._label.setMaximumHeight(120)
        self._label.setStyleSheet("font-size: 13px; color: #FFFFFF;")
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        h_layout.addWidget(self._label, stretch=1)

        self._layout.addWidget(wrapper)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色."""
        self._colors = colors
        super().refresh_theme(colors)
        primary = colors.get("primary_text", "#FFFFFF")
        bubble_fill = colors.get("chat_bubble_fill", "#2F2F2F")

        if hasattr(self, "_label") and self._role == "user":
            self._label.setStyleSheet(f"""
                font-size: 13px;
                color: {primary};
                background-color: {bubble_fill};
                border-radius: 18px;
                padding: 10px 14px;
            """)
        elif hasattr(self, "_label"):
            self._label.setStyleSheet(f"font-size: 13px; color: {primary};")

        if hasattr(self, "_dot"):
            self._dot.setStyleSheet(f"font-size: 6px; color: {primary};")

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
