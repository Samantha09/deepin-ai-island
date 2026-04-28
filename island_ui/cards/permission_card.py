from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.events import PermissionRequested, PermissionResolved


class PermissionCard(EventCard):
    responded = Signal(PermissionResolved)

    def __init__(self, event: PermissionRequested, parent: QWidget = None):
        super().__init__(event, parent)
        action = event.payload.get("action", "Unknown action")
        self.set_content("Permission Request", f"Allow {action}?")

        # 提取 tool_use_id，用于 socket 回传决策
        self._tool_use_id = event.payload.get("tool_use_id", "")

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._deny_btn = QPushButton("Deny")
        self._deny_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #eeeeee;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
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
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self._allow_btn.clicked.connect(self._on_allow)
        btn_layout.addWidget(self._allow_btn)

        self._layout.addLayout(btn_layout)

    def tool_use_id(self) -> str:
        return self._tool_use_id

    def _on_deny(self) -> None:
        response = PermissionResolved(approved=False, session_id=self._event.session_id)
        self.responded.emit(response)
        self.mark_resolved()

    def _on_allow(self) -> None:
        response = PermissionResolved(approved=True, session_id=self._event.session_id)
        self.responded.emit(response)
        self.mark_resolved()
