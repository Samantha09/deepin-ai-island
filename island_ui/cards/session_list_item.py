from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

from island_ui.session import Session


class SessionListItem(QFrame):
    clicked = Signal(str)
    hovered = Signal(str)

    _STATUS_KEYS = {
        "running": "status_running",
        "needs_attention": "status_needs_attention",
        "completed": "status_completed",
        "idle": "status_needs_attention",
    }

    _AGENT_COLORS = {
        "claude": ("#60A5FA", "rgba(96,165,250,0.12)"),
        "codex": ("#FF8C00", "rgba(255,140,0,0.12)"),
        "cmux": ("#8FCBF7", "rgba(143,203,247,0.12)"),
        "ghostty": ("#B399FF", "rgba(179,153,255,0.12)"),
        "iterm": ("#4ADE80", "rgba(74,222,128,0.12)"),
        "warp": ("#F59E0B", "rgba(245,158,11,0.12)"),
        "cursor": ("#66E8F8", "rgba(102,232,248,0.12)"),
        "kitty": ("#F08080", "rgba(240,128,128,0.12)"),
    }

    def __init__(self, session: Session, parent: QWidget = None):
        super().__init__(parent)
        self._session = session
        self._colors: dict[str, str] = {}
        self._active = False
        self.setMouseTracking(True)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.NoFrame)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 单行紧凑布局
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 10, 6)
        row_layout.setSpacing(8)

        # Status dot (6px)
        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 6px;")
        self._dot.setFixedSize(6, 6)
        self._dot_shadow = QGraphicsDropShadowEffect(self._dot)
        self._dot_shadow.setBlurRadius(3)
        self._dot_shadow.setColor(QColor(0, 0, 0, 128))
        self._dot_shadow.setOffset(0, 0)
        self._dot.setGraphicsEffect(self._dot_shadow)
        row_layout.addWidget(self._dot)

        # Name label
        self._name_label = QLabel(self._session.name)
        self._name_label.setStyleSheet("font-size: 13px; color: #FFFFFF; font-weight: 500;")
        row_layout.addWidget(self._name_label, stretch=1)

        # Right: agent tag + duration
        self._tags_label = QLabel("")
        self._tags_label.setStyleSheet("background: transparent;")
        row_layout.addWidget(self._tags_label)

        root_layout.addWidget(row)

        # 悬停展开区域
        self._expand_area = QWidget()
        expand_layout = QVBoxLayout(self._expand_area)
        expand_layout.setContentsMargins(10, 0, 10, 6)
        expand_layout.setSpacing(4)

        self._expand_label = QLabel("")
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._expand_label.setWordWrap(True)
        expand_layout.addWidget(self._expand_label)

        self._expand_area.setVisible(False)
        root_layout.addWidget(self._expand_area)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def _setup_style(self) -> None:
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)
        self._update_style()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        key = self._STATUS_KEYS.get(self._session.status, "status_needs_attention")
        color = colors.get(key, colors.get("secondary_text", "#8e8e93"))
        self._dot.setStyleSheet(f"color: {color}; font-size: 6px;")
        self._dot_shadow.setColor(QColor(color))

        self._name_label.setStyleSheet(
            f"font-size: {'13px' if self._active else '12px'}; "
            f"color: {colors['primary_text']}; "
            f"font-weight: {'600' if self._active else '500'};"
        )
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._tags_label.setText(self._build_tags(colors))
        self._update_style()

    def _update_style(self) -> None:
        if not self._colors:
            return
        # MioIsland: 无边框，仅靠细微背景色区分
        if self._active:
            bg = "rgba(255,255,255,0.05)"
        else:
            bg = "transparent"
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {bg};"
            f"  border-radius: 6px;"
            f"  border: none;"
            f"}}"
        )

    def enterEvent(self, event) -> None:
        self._show_expand()
        self.hovered.emit(self._session.id)
        if self._colors:
            self.setStyleSheet(
                f"QFrame {{"
                f"  background-color: rgba(255,255,255,0.08);"
                f"  border-radius: 6px;"
                f"  border: none;"
                f"}}"
            )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._expand_area.setVisible(False)
        self._update_style()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self._expand_area.isVisible():
            self._show_expand()
        super().mouseMoveEvent(event)

    def _show_expand(self) -> None:
        self._expand_label.setText(self._build_summary())
        self._expand_area.setVisible(True)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._session.id)
        super().mousePressEvent(event)

    def session(self) -> Session:
        return self._session

    def _build_summary(self) -> str:
        events = self._session.events
        lines: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()

        def add_line(role: str, text: str, kind: str) -> None:
            text = text.strip()
            if not text:
                return
            key = (kind, text)
            if key in seen:
                return
            seen.add(key)
            lines.append((role, text, kind))

        for event in events:
            if event.type == "chat.message":
                kind = event.payload.get("role", "assistant")
                role = "You" if kind == "user" else self._session.agent
                text = event.payload.get("content", "")
                add_line(role, text, kind)
            elif event.type == "permission.requested":
                action = event.payload.get("action", "")
                text = f"我需要 {action}，可以吗？" if action else "我需要一个权限，可以吗？"
                add_line(self._session.agent, text, "agent")
            elif event.type == "question.asked":
                question = event.payload.get("question", "")
                text = question if question else "我有一个问题想问你"
                add_line(self._session.agent, text, "agent")
            elif event.type == "progress.updated":
                msg = event.payload.get("message", "")
                if msg and msg not in ("idle",) and not msg.startswith(("等待批准", "已完成")):
                    add_line(self._session.agent, msg, "agent")

        dialogue_lines = [l for l in lines if l[2] != "system"]
        selected = dialogue_lines[-4:] if len(dialogue_lines) >= 2 else lines[-4:]

        if not selected:
            return '<div style="text-align: center; color: #666666; font-size: 12px; padding: 6px 0;">暂无聊天记录</div>'

        user_color = "#D1D5DB"
        assistant_color = "#FFFFFF"

        html_parts = []
        for role, text, kind in selected:
            if len(text) > 60:
                text = text[:57] + "..."
            color = user_color if kind == "user" else assistant_color
            html_parts.append(
                f'<div style="margin: 1px 0; font-size: 12px; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">'
                f'<span style="color: {color}; font-weight: 500;">{role}:</span>'
                f'<span style="color: {color}; margin-left: 4px; opacity: 0.85;">{text}</span>'
                f'</div>'
            )

        return "".join(html_parts)

    def _build_tags(self, colors: dict[str, str] | None = None) -> str:
        if colors is None:
            colors = self._colors if self._colors else {}
        agent_lower = self._session.agent.lower()
        text_color, bg_color = "#9A9A9A", "rgba(255,255,255,0.06)"
        for key, (tc, bc) in self._AGENT_COLORS.items():
            if key in agent_lower:
                text_color, bg_color = tc, bc
                break
        time_color = colors.get("muted_text", "#636366")
        return f"""
            <span style="background-color: {bg_color};
                         color: {text_color};
                         border-radius: 3px;
                         padding: 1px 5px;
                         font-size: 9px;
                         font-weight: 600;">
                {self._session.agent}
            </span>
            <span style="color: {time_color}; font-size: 9px; margin-left: 3px;">
                {self._session.duration_text()}
            </span>
        """

    def update_status(self) -> None:
        if self._colors:
            self.refresh_theme(self._colors)
        else:
            self._dot.setStyleSheet("color: #8e8e93; font-size: 6px;")
            self._tags_label.setText(self._build_tags())
