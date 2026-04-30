from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

from island_ui.session import Session


class SessionListItem(QFrame):
    clicked = Signal(str)  # emits session_id
    hovered = Signal(str)  # emits session_id

    _STATUS_KEYS = {
        "running": "status_running",
        "needs_attention": "status_needs_attention",
        "completed": "status_completed",
        "idle": "status_needs_attention",
    }

    # MioIsland 风格 agent / terminal 标签色
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

        # 顶部行
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(8, 10, 8, 10)
        top_layout.setSpacing(8)

        # Status dot (6px with shadow)
        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 6px;")
        self._dot.setFixedSize(6, 6)
        # Add shadow effect for status dot
        self._dot_shadow = QGraphicsDropShadowEffect(self._dot)
        self._dot_shadow.setBlurRadius(3)
        self._dot_shadow.setColor(QColor(0, 0, 0, 128))
        self._dot_shadow.setOffset(0, 0)
        self._dot.setGraphicsEffect(self._dot_shadow)
        top_layout.addWidget(self._dot)

        # Middle: name + description
        self._middle = QWidget()
        self._middle_layout = QVBoxLayout(self._middle)
        self._middle_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.setSpacing(2)

        self._name_label = QLabel(self._session.name)
        self._name_label.setStyleSheet("font-size: 13px; color: #FFFFFF; font-weight: 600;")
        self._middle_layout.addWidget(self._name_label)

        self._desc_label = QLabel("")
        self._desc_label.setStyleSheet("font-size: 11px; color: #9A9A9A;")
        self._desc_label.setWordWrap(True)
        self._middle_layout.addWidget(self._desc_label)
        self._refresh_desc()

        top_layout.addWidget(self._middle, stretch=1)

        # Right: agent tag + duration
        self._right = QWidget()
        self._right_layout = QVBoxLayout(self._right)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(4)
        self._right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._tags_label = QLabel("")
        self._tags_label.setStyleSheet("background: transparent;")
        self._right_layout.addWidget(self._tags_label)

        top_layout.addWidget(self._right)
        root_layout.addWidget(top_row)

        # 悬停展开区域（显示会话详情概要）- 保留用户此前要求的功能
        self._expand_area = QWidget()
        expand_layout = QVBoxLayout(self._expand_area)
        expand_layout.setContentsMargins(8, 0, 8, 8)
        expand_layout.setSpacing(6)

        self._expand_label = QLabel("")
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._expand_label.setWordWrap(True)
        expand_layout.addWidget(self._expand_label)

        self._expand_area.setVisible(False)
        root_layout.addWidget(self._expand_area)

    def set_active(self, active: bool) -> None:
        """切换活动(选中)状态样式."""
        self._active = active
        self._update_layout_margins()
        self._update_style()

    def _update_layout_margins(self) -> None:
        """根据活动状态调整内边距."""
        top_row = self._middle.parentWidget()
        layout = top_row.layout()
        if self._active:
            layout.setContentsMargins(8, 10, 8, 10)
        else:
            layout.setContentsMargins(8, 7, 8, 7)

    def _setup_style(self) -> None:
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(320)
        self.setMinimumHeight(40)
        self._update_style()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        key = self._STATUS_KEYS.get(self._session.status, "status_needs_attention")
        color = colors.get(key, colors.get("secondary_text", "#8e8e93"))
        self._dot.setStyleSheet(f"color: {color}; font-size: 6px;")
        self._dot_shadow.setColor(QColor(color))

        self._name_label.setStyleSheet(
            f"font-size: {'13px' if self._active else '11px'}; "
            f"color: {colors['primary_text']}; "
            f"font-weight: {'600' if self._active else '500'};"
        )
        self._desc_label.setStyleSheet(
            f"font-size: 11px; color: {colors['secondary_text']};"
        )
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._tags_label.setText(self._build_tags(colors))
        self._update_style()

    def _update_style(self) -> None:
        if not self._colors:
            return
        card_bg = self._colors.get("card_bg", "#1A1A1A")
        card_border = self._colors.get("card_border", "#2A2A2A")
        radius = 8 if self._active else 6
        if self._active:
            accent = self._colors.get("accent_amber", "#F59E0B")
            bg = f"rgba({self._hex_to_rgb(accent)},0.05)"
            border = f"rgba({self._hex_to_rgb(accent)},0.15)"
        else:
            bg = card_bg
            border = card_border
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {bg};"
            f"  border-radius: {radius}px;"
            f"  border: 1px solid {border};"
            f"}}"
        )

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r},{g},{b}"

    def enterEvent(self, event) -> None:
        self._show_expand()
        self.hovered.emit(self._session.id)
        # Hover 背景变化
        if self._colors:
            accent = self._colors.get("accent_amber", "#F59E0B")
            hover_bg = f"rgba({self._hex_to_rgb(accent)},0.08)"
            self.setStyleSheet(
                f"QFrame {{"
                f"  background-color: {hover_bg};"
                f"  border-radius: {8 if self._active else 6}px;"
                f"  border: 1px solid rgba({self._hex_to_rgb(accent)},0.2);"
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
        """构建简洁的聊天记录行列表."""
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
            return '<div style="text-align: center; color: #666666; font-size: 13px; padding: 8px 0;">暂无聊天记录</div>'

        user_color = "#D1D5DB"
        assistant_color = "#FFFFFF"
        system_color = "#9A9A9A"

        html_parts = []
        for role, text, kind in selected:
            if len(text) > 60:
                text = text[:57] + "..."
            if kind == "user":
                rc = user_color
                tc = user_color
            elif kind == "system":
                rc = system_color
                tc = system_color
            else:
                rc = assistant_color
                tc = assistant_color

            html_parts.append(
                f'<div style="margin: 2px 0; font-size: 13px; line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">'
                f'<span style="color: {rc}; font-weight: 600; letter-spacing: 0.2px;">{role}:</span>'
                f'<span style="color: {tc}; margin-left: 6px;">{text}</span>'
                f'</div>'
            )

        return "".join(html_parts)

    def _build_tags(self, colors: dict[str, str] | None = None) -> str:
        if colors is None:
            colors = self._colors if self._colors else {}
        agent_lower = self._session.agent.lower()
        # 查找匹配的 agent 颜色
        text_color, bg_color = "#9A9A9A", "rgba(255,255,255,0.06)"
        for key, (tc, bc) in self._AGENT_COLORS.items():
            if key in agent_lower:
                text_color, bg_color = tc, bc
                break
        time_color = colors.get("muted_text", "#636366")
        return f"""
            <span style="background-color: {bg_color};
                         color: {text_color};
                         border-radius: 4px;
                         padding: 2px 6px;
                         font-size: 10px;
                         font-weight: 600;">
                {self._session.agent}
            </span>
            <span style="color: {time_color}; font-size: 10px; margin-left: 4px;">
                {self._session.duration_text()}
            </span>
        """

    def _refresh_desc(self) -> None:
        """仅显示 permission/question 具体内容，不显示纯状态文字."""
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
            self._dot.setStyleSheet("color: #8e8e93; font-size: 6px;")
            self._tags_label.setText(self._build_tags())
            self._refresh_desc()
