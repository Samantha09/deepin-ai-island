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
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(10)

        # 左侧选中指示条（默认隐藏）
        self._indicator = QFrame()
        self._indicator.setFixedWidth(3)
        self._indicator.setFixedHeight(0)
        self._indicator.setStyleSheet("background: transparent; border: none; border-radius: 2px;")
        self._layout.addWidget(self._indicator)

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
        self._name_label.setStyleSheet("font-size: 13px; color: #ffffff; font-weight: 500;")
        self._middle_layout.addWidget(self._name_label)

        self._desc_label = QLabel("")
        self._desc_label.setStyleSheet("font-size: 11px; color: #8e8e93;")
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

    def set_selected(self, selected: bool) -> None:
        """切换左侧 accent 指示条显示状态."""
        if selected:
            self._indicator.setFixedHeight(20)
            color = self._colors.get("accent_blue", "#007aff") if self._colors else "#007aff"
            self._indicator.setStyleSheet(
                f"background: {color}; border: none; border-radius: 2px;"
            )
        else:
            self._indicator.setFixedHeight(0)
            self._indicator.setStyleSheet("background: transparent; border: none; border-radius: 2px;")

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1c1c1e;
                border-radius: 10px;
                border: none;
            }
            QFrame:hover {
                background-color: #2c2c2e;
            }
            QFrame:pressed {
                background-color: #3a3a3c;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(340)
        self.setMinimumHeight(48)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        key = self._STATUS_KEYS.get(self._session.status, "status_needs_attention")
        color = colors.get(key, colors.get("secondary_text", "#8e8e93"))
        self._dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._name_label.setStyleSheet(
            f"font-size: 13px; color: {colors['primary_text']}; font-weight: 500;"
        )
        self._desc_label.setStyleSheet(
            f"font-size: 11px; color: {colors['secondary_text']};"
        )
        self._tags_label.setText(self._build_tags(colors))
        press_bg = colors.get("control_bg_hover", "#3a3a3c")
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {colors['card_bg']};"
            f"  border-radius: 10px;"
            f"  border: none;"
            f"}}"
            f"QFrame:hover {{"
            f"  background-color: {colors['card_bg_hover']};"
            f"}}"
            f"QFrame:pressed {{"
            f"  background-color: {press_bg};"
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
        tag_color = colors.get("secondary_text", "#8e8e93")
        time_color = colors.get("muted_text", "#636366")
        tag_bg = colors.get("control_bg", "#2c2c2e")
        return f"""
            <span style="background-color: {tag_bg};
                         color: {tag_color};
                         border-radius: 4px;
                         padding: 2px 6px;
                         font-size: 10px;">
                {self._session.agent}
            </span>
            <span style="color: {time_color}; font-size: 10px; margin-left: 4px;">
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
            self._dot.setStyleSheet("color: #8e8e93; font-size: 10px;")
            self._tags_label.setText(self._build_tags())
            self._refresh_desc()
