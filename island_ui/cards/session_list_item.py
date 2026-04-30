from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget,
)

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

    def __init__(self, session: Session, parent: QWidget = None):
        super().__init__(parent)
        self._session = session
        self._colors: dict[str, str] = {}
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
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(10)

        # 左侧选中指示条（默认隐藏）
        self._indicator = QFrame()
        self._indicator.setFixedWidth(3)
        self._indicator.setFixedHeight(0)
        self._indicator.setStyleSheet("background: transparent; border: none; border-radius: 2px;")
        top_layout.addWidget(self._indicator)

        # Status dot
        self._dot = QLabel("●")
        self._dot.setStyleSheet("font-size: 10px;")
        top_layout.addWidget(self._dot)

        # Middle: name + description
        self._middle = QWidget()
        self._middle_layout = QVBoxLayout(self._middle)
        self._middle_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.setSpacing(2)

        self._name_label = QLabel(self._session.name)
        self._name_label.setStyleSheet("font-size: 13px; color: #ffffff; font-weight: 500;")
        self._middle_layout.addWidget(self._name_label)

        self._desc_label = QLabel("")
        self._desc_label.setStyleSheet("font-size: 10px; color: #8e8e93;")
        self._desc_label.setWordWrap(True)
        self._middle_layout.addWidget(self._desc_label)
        self._refresh_desc()

        top_layout.addWidget(self._middle, stretch=1)

        # Right: agent + terminal + time tags
        self._right = QWidget()
        self._right_layout = QVBoxLayout(self._right)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(4)
        self._right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._tags_label = QLabel(self._build_tags())
        self._tags_label.setStyleSheet("background: transparent;")
        self._right_layout.addWidget(self._tags_label)

        top_layout.addWidget(self._right)
        root_layout.addWidget(top_row)

        # 悬停展开区域（显示会话详情概要）
        self._expand_area = QWidget()
        expand_layout = QVBoxLayout(self._expand_area)
        expand_layout.setContentsMargins(12, 0, 12, 8)
        expand_layout.setSpacing(6)

        self._expand_label = QLabel("")
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._expand_label.setWordWrap(True)
        expand_layout.addWidget(self._expand_label)

        self._expand_area.setVisible(False)
        root_layout.addWidget(self._expand_area)

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
                background-color: #0c0f14;
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.03);
            }
            QFrame:hover {
                background-color: #141820;
                border: 1px solid rgba(255,255,255,0.07);
            }
            QFrame:pressed {
                background-color: #1a1f26;
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
            f"font-size: 10px; color: {colors['secondary_text']};"
        )
        self._expand_label.setStyleSheet("background: transparent; border: none;")
        self._tags_label.setText(self._build_tags(colors))
        press_bg = colors.get("control_bg_hover", "#3a3a3c")
        card_border = colors.get("card_border", "rgba(255,255,255,0.03)")
        card_border_hover = colors.get("card_border_hover", "rgba(255,255,255,0.07)")
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {colors['card_bg']};"
            f"  border-radius: 16px;"
            f"  border: 1px solid {card_border};"
            f"}}"
            f"QFrame:hover {{"
            f"  background-color: {colors['card_bg_hover']};"
            f"  border: 1px solid {card_border_hover};"
            f"}}"
            f"QFrame:pressed {{"
            f"  background-color: {press_bg};"
            f"}}"
        )

    def enterEvent(self, event) -> None:
        self._show_expand()
        self.hovered.emit(self._session.id)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._expand_area.setVisible(False)
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
        """构建简洁的聊天记录行列表，参考 VibeAgentIsland 风格。"""
        events = self._session.events
        lines: list[tuple[str, str, str]] = []  # (role, text, kind)
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
                # 过滤掉纯状态消息，只保留有意义的进度内容
                if msg and msg not in ("idle",) and not msg.startswith(("等待批准", "已完成")):
                    add_line(self._session.agent, msg, "agent")

        # 优先取对话行（非 system），不够再补 system
        dialogue_lines = [l for l in lines if l[2] != "system"]
        selected = dialogue_lines[-4:] if len(dialogue_lines) >= 2 else lines[-4:]

        if not selected:
            return '<div style="text-align: center; color: #76818d; font-size: 11px; padding: 8px 0;">暂无聊天记录</div>'

        # 颜色配置（参考 VibeAgentIsland）
        agent_colors = {
            "claude code": "#d28d80",
            "codex": "#8ab8d4",
            "gemini": "#b3a6ff",
            "cursor": "#8ee7cf",
            "opencode": "#ffc58d",
        }
        agent_key = self._session.agent.lower()
        role_color = agent_colors.get(agent_key, "#d28d80")  # 默认暖色
        user_color = "#f1d8b8"
        assistant_text_color = "#8f98a2"
        completed_text_color = "#d7efe3"
        system_speaker_color = "#97a2ad"
        system_text_color = "#76818d"
        is_completed = self._session.status == "completed"

        html_parts = []
        for role, text, kind in selected:
            if len(text) > 60:
                text = text[:57] + "..."
            if kind == "user":
                rc = user_color
                tc = "#e5d9cb"
            elif kind == "system":
                rc = system_speaker_color
                tc = system_text_color
            else:
                rc = role_color
                tc = completed_text_color if is_completed else assistant_text_color

            html_parts.append(
                f'<div style="margin: 1px 0; font-size: 10px; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">'
                f'<span style="color: {rc}; font-weight: bold; letter-spacing: 0.2px;">{role}:</span>'
                f'<span style="color: {tc}; margin-left: 6px;">{text}</span>'
                f'</div>'
            )

        return "".join(html_parts)

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
