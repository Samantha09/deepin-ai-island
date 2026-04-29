from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget,
)

from island_ui.session import Session


class SessionListItem(QFrame):
    clicked = Signal(str)  # emits session_id

    _STATUS_KEYS = {
        "running": "status_running",
        "needs_attention": "status_needs_attention",
        "completed": "status_completed",
        "idle": "status_needs_attention",
    }

    def __init__(self, session: Session, parent: QWidget = None):
        super().__init__(parent)
        self._session = session
        self._colors: dict[str, str] = {}
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(10)

        # Status dot
        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 10px;")
        self._layout.addWidget(self._dot)

        # Middle: name + description
        self._middle = QWidget()
        self._middle_layout = QVBoxLayout(self._middle)
        self._middle_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.setSpacing(2)

        self._name_label = QLabel(self._session.name)
        self._name_label.setStyleSheet("font-size: 14px; color: #eeeeee; font-weight: 500;")
        self._middle_layout.addWidget(self._name_label)

        self._desc_label = QLabel("")
        self._desc_label.setStyleSheet("font-size: 11px; color: #888888;")
        self._desc_label.setWordWrap(True)
        self._middle_layout.addWidget(self._desc_label)
        self._refresh_desc()

        self._layout.addWidget(self._middle, stretch=1)

        # Right: agent + terminal + time tags
        self._right = QWidget()
        self._right_layout = QVBoxLayout(self._right)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(4)
        self._right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._tags_label = QLabel(self._build_tags())
        self._tags_label.setStyleSheet("background: transparent;")
        self._right_layout.addWidget(self._tags_label)

        self._layout.addWidget(self._right)

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            SessionListItem {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 10px;
                border: none;
            }
            SessionListItem:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(340)
        self.setMinimumHeight(58)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        key = self._STATUS_KEYS.get(self._session.status, "status_needs_attention")
        color = colors.get(key, colors.get("secondary_text", "#888888"))
        self._dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._name_label.setStyleSheet(
            f"font-size: 14px; color: {colors['primary_text']}; font-weight: 500;"
        )
        self._desc_label.setStyleSheet(
            f"font-size: 11px; color: {colors['secondary_text']};"
        )
        self._tags_label.setText(self._build_tags(colors))
        self.setStyleSheet(
            f"SessionListItem {{"
            f"  background-color: {colors['card_bg']};"
            f"  border-radius: 10px;"
            f"  border: none;"
            f"}}"
            f"SessionListItem:hover {{"
            f"  background-color: {colors['card_bg_hover']};"
            f"}}"
        )

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._session.id)
        super().mousePressEvent(event)

    def session(self) -> Session:
        return self._session

    def _build_tags(self, colors: dict[str, str] | None = None) -> str:
        if colors is None:
            colors = self._colors if self._colors else {}
        tag_color = colors.get("secondary_text", "#aaaaaa")
        time_color = colors.get("secondary_text", "#666666")
        return f"""
            <span style="background-color: rgba(255,255,255,0.08);
                         color: {tag_color};
                         border-radius: 4px;
                         padding: 2px 6px;
                         font-size: 11px;">
                {self._session.agent}
            </span>
            <span style="background-color: rgba(255,255,255,0.08);
                         color: {tag_color};
                         border-radius: 4px;
                         padding: 2px 6px;
                         font-size: 11px;">
                {self._session.terminal}
            </span>
            <span style="color: {time_color}; font-size: 11px; margin-left: 4px;">
                {self._session.duration_text()}
            </span>
        """

    def _refresh_desc(self) -> None:
        """仅显示 permission/question 具体内容，不显示纯状态文字。"""
        last = self._session.last_event()
        desc = ""
        if last:
            if last.type == "permission.requested":
                desc = last.payload.get("action", "")
            elif last.type == "question.asked":
                desc = last.payload.get("question", "")
            elif last.type == "progress.updated":
                msg = last.payload.get("message", "")
                if msg.startswith("等待批准"):
                    desc = msg[6:].strip() if msg.startswith("等待批准:") else msg
        self._desc_label.setText(desc)
        self._desc_label.setVisible(bool(desc))

    def update_status(self) -> None:
        """Refresh dot color and tags from current session state."""
        if self._colors:
            self.refresh_theme(self._colors)
        else:
            self._dot.setStyleSheet("color: #888888; font-size: 10px;")
            self._tags_label.setText(self._build_tags())
            self._refresh_desc()
