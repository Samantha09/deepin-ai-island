from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget, QLabel, QVBoxLayout

from island_ui.cards.base_card import EventCard
from island_ui.events import PermissionRequested, PermissionResolved


class PermissionCard(EventCard):
    responded = Signal(PermissionResolved)
    open_chat = Signal(str)  # session_id

    def __init__(self, event: PermissionRequested, parent: QWidget = None):
        super().__init__(event, parent)
        tool = event.payload.get("tool", "Unknown")
        tool_input = event.payload.get("tool_input", {})
        action = event.payload.get("action", "")

        # 提取 tool_use_id，用于 socket 回传决策
        self._tool_use_id = event.payload.get("tool_use_id", "")

        # Header: amber dot + title + source badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet("color: #FF9800; font-size: 10px;")
        header_layout.addWidget(dot)

        title = QLabel("Permission Request")
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        header_layout.addWidget(title)

        badge = QLabel("CLAUDE")
        badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 152, 0, 0.15);
                color: #FF9800;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(badge)
        header_layout.addStretch()
        self._layout.addLayout(header_layout)

        # Tool name (monospaced, amber)
        tool_label = QLabel(tool)
        tool_label.setStyleSheet("""
            font-size: 12px;
            font-family: 'DejaVu Sans Mono', 'Noto Mono', monospace;
            font-weight: 500;
            color: #FF9800;
        """)
        self._layout.addWidget(tool_label)

        # Tool input preview
        input_preview = self._format_input(tool, tool_input)
        if input_preview:
            input_label = QLabel(input_preview)
            input_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.5);")
            input_label.setWordWrap(True)
            self._layout.addWidget(input_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._chat_btn = QPushButton("Open Chat")
        self._chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #eeeeee;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self._chat_btn.clicked.connect(self._on_open_chat)
        btn_layout.addWidget(self._chat_btn)

        btn_layout.addStretch()

        self._deny_btn = QPushButton("Deny")
        self._deny_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #eeeeee;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self._deny_btn.clicked.connect(self._on_deny)
        btn_layout.addWidget(self._deny_btn)

        self._allow_btn = QPushButton("Allow")
        self._allow_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.92);
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #ffffff;
            }
        """)
        self._allow_btn.clicked.connect(self._on_allow)
        btn_layout.addWidget(self._allow_btn)

        self._layout.addLayout(btn_layout)

    def tool_use_id(self) -> str:
        return self._tool_use_id

    @staticmethod
    def _format_input(tool: str, tool_input: dict) -> str:
        if tool == "Bash":
            return tool_input.get("command", "")[:120]
        if tool in ("Edit", "Write", "MultiEdit"):
            path = tool_input.get("path", tool_input.get("file_path", ""))
            return path
        if tool == "Read":
            return tool_input.get("path", "")
        return ""

    def _on_open_chat(self) -> None:
        self.open_chat.emit(self._event.session_id)

    def _on_deny(self) -> None:
        response = PermissionResolved(approved=False, session_id=self._event.session_id)
        self.responded.emit(response)
        self.mark_resolved()

    def _on_allow(self) -> None:
        response = PermissionResolved(approved=True, session_id=self._event.session_id)
        self.responded.emit(response)
        self.mark_resolved()
