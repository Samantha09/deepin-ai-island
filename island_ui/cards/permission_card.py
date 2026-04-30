from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget, QLabel, QVBoxLayout

from island_ui.cards.base_card import EventCard
from island_ui.components.styled_button import StyledButton
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
        self._colors: dict[str, str] = {}

        # Header: amber dot + title + source badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(self._dot)

        self._title = QLabel("Permission Request")
        self._title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        header_layout.addWidget(self._title)

        self._badge = QLabel("CLAUDE")
        self._badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 152, 0, 0.15);
                color: #FF9800;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(self._badge)
        header_layout.addStretch()
        self._layout.addLayout(header_layout)

        # Tool name (monospaced, amber)
        self._tool_label = QLabel(tool)
        self._tool_label.setStyleSheet("""
            font-size: 12px;
            font-family: 'DejaVu Sans Mono', 'Noto Mono', monospace;
            font-weight: 500;
            color: #FF9800;
        """)
        self._layout.addWidget(self._tool_label)

        # Tool input preview
        input_preview = self._format_input(tool, tool_input)
        if input_preview:
            self._input_label = QLabel(input_preview)
            self._input_label.setStyleSheet("font-size: 11px; color: #9A9A9A;")
            self._input_label.setWordWrap(True)
            self._layout.addWidget(self._input_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._chat_btn = StyledButton("Open Chat", variant="ghost")
        self._chat_btn.clicked.connect(self._on_open_chat)
        btn_layout.addWidget(self._chat_btn)

        btn_layout.addStretch()

        self._deny_btn = StyledButton("Deny", variant="secondary")
        self._deny_btn.clicked.connect(self._on_deny)
        btn_layout.addWidget(self._deny_btn)

        self._allow_btn = StyledButton("Allow", variant="primary")
        self._allow_btn.clicked.connect(self._on_allow)
        btn_layout.addWidget(self._allow_btn)

        self._layout.addLayout(btn_layout)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        accent = colors.get("accent_amber", "#F59E0B")
        primary = colors.get("primary_text", "#FFFFFF")
        secondary = colors.get("secondary_text", "#9A9A9A")
        overlay = colors.get("card_bg", "#1A1A1A")
        border = colors.get("card_border", "#2A2A2A")
        allow_bg = colors.get("accent_green", "#4ADE80")
        inverse = colors.get("inverse_text", "#000000")
        # MioIsland ChatApprovalBar 背景色
        approval_bg = "#1A1A2E"

        # 重写卡片背景为 approval bar 深色
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {approval_bg};"
            f"  border-radius: 16px;"
            f"  border: 1px solid {border};"
            f"}}"
        )

        self._dot.setStyleSheet(f"color: {accent}; font-size: 10px;")
        self._title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {primary};"
        )
        self._badge.setStyleSheet(f"""
            QLabel {{
                background-color: {self._hex_to_rgba(accent, 0.15)};
                color: {accent};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }}
        """)
        self._tool_label.setStyleSheet(f"""
            font-size: 12px;
            font-family: 'DejaVu Sans Mono', 'Noto Mono', monospace;
            font-weight: 500;
            color: {accent};
        """)
        if hasattr(self, "_input_label"):
            self._input_label.setStyleSheet(
                f"font-size: 11px; color: {secondary};"
            )
        self._chat_btn.refresh_theme(colors)
        # Deny 按钮：MioIsland 风格 — overlay 背景 + border 描边
        self._deny_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {overlay};
                color: {primary};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {colors.get('card_bg_hover', '#2A2A2A')};
                border: 1px solid {colors.get('card_border_hover', '#3A3A3A')};
            }}
        """)
        # Allow 按钮：MioIsland 风格 — 绿色填充 + 黑字
        self._allow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {allow_bg};
                color: {inverse};
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #5EE68F;
            }}
        """)

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

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
