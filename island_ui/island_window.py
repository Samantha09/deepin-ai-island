import os
import sys
from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QObject, Signal, Slot, QRect, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtGui import QColor

from island_ui.state_machine import IslandStateMachine, IslandState
from island_ui.event_source import EventSource
from island_ui.events import Event, SessionStarted, SessionEnded, ChatMessage
from island_ui.session import Session


class IslandBridge(QObject):
    """JS -> Python 桥接对象（主窗口）"""

    def __init__(self, window: "IslandWindow") -> None:
        super().__init__()
        self.window = window

    @Slot(bool)
    def setHovered(self, hovered: bool) -> None:
        self.window.set_hovered(hovered)

    @Slot(str)
    def selectSession(self, session_id: str) -> None:
        self.window.select_session(session_id)

    @Slot(str, bool)
    def respondPermission(self, session_id: str, approved: bool) -> None:
        self.window.respond_permission(session_id, approved)

    @Slot(str)
    def closeSession(self, session_id: str) -> None:
        self.window.close_session(session_id)

    @Slot()
    def openExpandedWindow(self) -> None:
        self.window.open_expanded_window()


class ExpandedBridge(QObject):
    """JS -> Python 桥接对象（展开窗口）"""

    def __init__(self, window: "ExpandedWindow") -> None:
        super().__init__()
        self.window = window

    @Slot()
    def closeExpandedWindow(self) -> None:
        self.window.close_to_main()

    @Slot(str, bool)
    def respondPermission(self, session_id: str, approved: bool) -> None:
        self.window.main_window.respond_permission(session_id, approved)


class ExpandedWindow(QWidget):
    """展开面板窗口：承载详情页面"""

    def __init__(self, main_window: "IslandWindow") -> None:
        super().__init__()
        self.main_window = main_window
        self.target_size = (380, 420)
        self.setWindowFlags(main_window.base_flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.NoContextMenu)
        self.web_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent; border: none;")
        self.web_view.page().setBackgroundColor(Qt.transparent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)

        # WebEngine 轻量化配置
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        profile = self.web_view.page().profile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setHttpCacheMaximumSize(10 * 1024 * 1024)

        self.bridge = ExpandedBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pyisland", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "expanded.html")
        self.web_view.load(QUrl.fromLocalFile(html_path))
        self.web_view.hide()

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(220)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.content_timer = QTimer(self)
        self.content_timer.setSingleShot(True)
        self.content_timer.timeout.connect(self._show_web_content)

        self._closing = False
        self._opening = False
        self._close_timer: Optional[QTimer] = None

    def open_from(self, source_rect: QRect) -> None:
        # 取消任何 pending 的关闭操作，避免快速切换卡片时旧 timer 把新窗口 hide 掉
        if self._close_timer is not None:
            self._close_timer.stop()
            self._close_timer = None
        self._closing = False
        self._opening = True
        self.content_timer.stop()
        target_w, target_h = self.target_size
        screen_geo = QApplication.primaryScreen().availableGeometry()
        target_x = screen_geo.x() + (screen_geo.width() - target_w) // 2
        target_y = max(screen_geo.y() + self.main_window.top_margin, source_rect.y())
        self._target_rect = QRect(target_x, target_y, target_w, target_h)
        start_w = max(source_rect.width(), 120)
        start_h = max(source_rect.height(), 45)
        start_x = self._target_rect.center().x() - start_w // 2
        start_y = self._target_rect.center().y() - start_h // 2
        self.setGeometry(QRect(start_x, start_y, start_w, start_h))
        self.web_view.hide()
        self.show()
        self.raise_()
        self.activateWindow()
        self.content_timer.start(360)
        QTimer.singleShot(80, self._start_open_animation)

    def _start_open_animation(self) -> None:
        if not self.isVisible() or self._closing:
            return
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self._target_rect)
        self.animation.start()

    def _show_web_content(self) -> None:
        if not self.isVisible() or self._closing:
            return
        self.web_view.show()
        self.web_view.page().runJavaScript(
            "if (typeof window.playEntrance === 'function') { window.playEntrance(); }"
        )
        self._opening = False

    def close_to_main(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.content_timer.stop()
        self.animation.stop()
        self.web_view.hide()
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._finish_close_to_main)
        self._close_timer.start(70)

    def _finish_close_to_main(self) -> None:
        self._close_timer = None
        if not self._closing:
            return
        self.hide()
        self.main_window.raise_()
        self.main_window.activateWindow()
        self._closing = False
        self.main_window.on_expanded_closed()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if not self._opening:
            self.close_to_main()

    def update_session_detail(self, session: Session) -> None:
        """推送会话详情到前端"""
        import json
        events_data = []
        for event in session.events[-20:]:
            events_data.append({
                "type": event.type,
                "payload": event.payload,
            })
        data = {
            "id": session.id,
            "name": session.name,
            "agent": session.agent,
            "status": session.status,
            "events": events_data,
            "resolved_tool_use_ids": list(session.resolved_tool_use_ids),
        }
        js = f"if (typeof window.updateSessionDetail === 'function') window.updateSessionDetail({json.dumps(data, ensure_ascii=False)});"
        self.web_view.page().runJavaScript(js)


class IslandWindow(QWidget):
    """主窗口：透明置顶 + QWebEngine 承载前端页面（Python-island 风格）"""

    def __init__(
        self,
        event_source: EventSource,
        state_machine: IslandStateMachine,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._event_source = event_source
        self._state_machine = state_machine
        self._agents: set[str] = set()
        self._sessions: dict[str, Session] = {}

        self.small_size = (320, 45)
        self.large_size = (320, 320)
        self.top_margin = 16
        self._hovered = False
        self._native_fixed = False
        self._expanded_open = False

        self.base_flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.NoDropShadowWindowHint
        )
        self.setWindowFlags(self.base_flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        # Web 容器
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.NoContextMenu)
        self.web_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.web_view.setAttribute(Qt.WA_NoSystemBackground, True)
        self.web_view.setStyleSheet("background: transparent; border: none;")
        self.web_view.page().setBackgroundColor(Qt.transparent)

        # WebEngine 轻量化配置
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        profile = self.web_view.page().profile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setHttpCacheMaximumSize(10 * 1024 * 1024)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)

        # 注册 JS <-> Python 桥接
        self.bridge = IslandBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pyisland", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "island.html")
        self.web_view.load(QUrl.fromLocalFile(html_path))

        self.expanded_window = ExpandedWindow(self)

        # 窗口几何动画
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(240)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_target: Optional[tuple[int, int]] = None

        initial_rect = self._target_rect(*self.small_size)
        self.setGeometry(initial_rect)

        # 事件连接
        self._event_source.event_received.connect(self._on_event)
        self._state_machine.state_changed.connect(self._on_state_changed)

        # 清理定时器
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setSingleShot(True)
        self.cleanup_timer.timeout.connect(self.compact_memory)

        # 自动缩回
        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.timeout.connect(self._on_delayed_leave)

        # 审批自动弹出后的 5s 自动关闭
        self._permission_auto_close_timer = QTimer(self)
        self._permission_auto_close_timer.setSingleShot(True)
        self._permission_auto_close_timer.timeout.connect(self._on_permission_auto_close)

        # 防抖定时器：避免鼠标在边界快速进出导致动画抖动
        self._hover_debounce_timer = QTimer(self)
        self._hover_debounce_timer.setSingleShot(True)
        self._hover_debounce_timer.timeout.connect(self._apply_hovered)
        self._pending_hovered: Optional[bool] = None

        # 轮询兜底（只负责 leave_timer，不直接触发 hover 状态）
        self._hover_timer = QTimer(self)
        self._hover_timer.timeout.connect(self._check_hover)
        self._hover_timer.start(100)

    def _target_rect(self, width: int, height: int) -> QRect:
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        x = screen_geo.x() + (screen_geo.width() - width) // 2
        y = screen_geo.y() + self.top_margin
        return QRect(x, y, width, height)

    def animate_to(self, width: int, height: int) -> None:
        target_rect = self._target_rect(width, height)
        # 如果已经在目标尺寸，不启动动画
        if self.geometry() == target_rect:
            return
        # 如果当前动画正在向同一目标运行，不重启动画
        if self.animation.state() == QPropertyAnimation.State.Running and self._anim_target == (width, height):
            return
        self._anim_target = (width, height)
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(target_rect)
        self.animation.start()
        self.schedule_cleanup()

    def set_hovered(self, hovered: bool) -> None:
        """由前端 JS 调用，带 80ms 防抖避免快速切换导致抖动."""
        self._pending_hovered = hovered
        self._hover_debounce_timer.stop()
        self._hover_debounce_timer.start(80)

    def _apply_hovered(self) -> None:
        """执行防抖后的 hover 状态切换."""
        hovered = self._pending_hovered
        if hovered is None or self._hovered == hovered:
            return
        self._hovered = hovered
        target = self.large_size if hovered else self.small_size
        self.animate_to(*target)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_event(self, event: Event) -> None:
        self._state_machine.on_event_arrived()

        agent = event.payload.get("agent")
        if agent:
            self._agents.add(agent)

        if isinstance(event, SessionStarted):
            existing = self._sessions.get(event.session_id)
            if existing:
                existing.status = "running"
                existing.add_event(event)
            else:
                session = Session(
                    id=event.session_id,
                    name=event.payload.get("task", "Untitled"),
                    agent=agent or "Unknown",
                    terminal=event.payload.get("terminal", "Terminal"),
                    start_time=event.timestamp,
                )
                self._sessions[event.session_id] = session
            self._push_sessions_to_web()
            return

        if isinstance(event, SessionEnded):
            session = self._sessions.get(event.session_id)
            if session:
                session.status = "completed"
                session.add_event(event)
            self._push_sessions_to_web()
            return

        session = self._sessions.get(event.session_id)
        if not session and event.type in ("chat.message", "permission.requested", "question.asked"):
            # 自动恢复被关闭的活跃会话
            session = Session(
                id=event.session_id,
                name=event.payload.get("task", event.session_id[:8]),
                agent=event.payload.get("agent", "Unknown"),
                terminal=event.payload.get("terminal", ""),
                start_time=event.timestamp,
            )
            self._sessions[event.session_id] = session
        if session:
            session.add_event(event)

        # 审批事件自动弹开
        if event.type == "permission.requested":
            self._auto_expand_for_permission(event.session_id)

        self._push_sessions_to_web()

    def _auto_expand_for_permission(self, session_id: str) -> None:
        if not self.expanded_window.isVisible():
            self.select_session(session_id)
            self._permission_auto_close_timer.stop()
            self._permission_auto_close_timer.start(5000)

    def _on_permission_auto_close(self) -> None:
        if self.expanded_window.isVisible():
            self.expanded_window.close_to_main()

    def _build_session_summary(self, session: Session) -> str:
        """从会话事件中提取 1-2 行简短工作概要。"""
        summaries: list[str] = []
        for event in reversed(session.events):
            if event.type == "chat.message":
                content = event.payload.get("content", "")
                role = event.payload.get("role", "assistant")
                prefix = "你" if role == "user" else "AI"
                text = content[:50] + "..." if len(content) > 50 else content
                summaries.append(f"{prefix}: {text}")
            elif event.type == "permission.requested":
                action = event.payload.get("action", "")
                text = action[:50] + "..." if len(action) > 50 else action
                summaries.append(f"需要审批: {text}")
            elif event.type == "progress.updated":
                msg = event.payload.get("message", "")
                if msg and msg != "idle":
                    summaries.append(msg[:50])
            if len(summaries) >= 2:
                break
        return " · ".join(reversed(summaries))

    def _push_sessions_to_web(self) -> None:
        import json
        waiting_sessions = []
        running_sessions = []
        other_sessions = []
        for session in self._sessions.values():
            if session.status == "needs_attention":
                waiting_sessions.append(session)
            elif session.status == "running":
                running_sessions.append(session)
            else:
                other_sessions.append(session)

        # 每组按最后更新时间降序排列
        for group in (waiting_sessions, running_sessions, other_sessions):
            group.sort(key=lambda s: s.last_updated, reverse=True)

        sessions_data = []
        for session in waiting_sessions + running_sessions + other_sessions:
            waiting_action = ""
            if session.status == "needs_attention":
                # 查找最近的未解决 permission 事件
                for event in reversed(session.events):
                    if event.type == "permission.requested":
                        tid = event.payload.get("tool_use_id", "")
                        if not session.is_permission_resolved(tid):
                            waiting_action = event.payload.get("action", "")
                            break
            sessions_data.append({
                "id": session.id,
                "name": session.name,
                "agent": session.agent,
                "status": session.status,
                "waiting_action": waiting_action,
                "summary": self._build_session_summary(session),
            })

        total = len(self._sessions)
        active = sum(1 for s in self._sessions.values() if s.status not in ("completed", "idle"))
        waiting = sum(1 for s in self._sessions.values() if s.status == "needs_attention")

        data = {
            "sessions": sessions_data,
            "total": total,
            "active": active,
            "waiting": waiting,
        }
        js = f"if (typeof window.updateSessions === 'function') window.updateSessions({json.dumps(data, ensure_ascii=False)});"
        self.web_view.page().runJavaScript(js)

    # ------------------------------------------------------------------
    # User interactions from JS
    # ------------------------------------------------------------------

    def select_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        self._permission_auto_close_timer.stop()
        self.expanded_window.update_session_detail(session)
        self.open_expanded_window()

    def respond_permission(self, session_id: str, approved: bool) -> None:
        self._permission_auto_close_timer.stop()
        session = self._sessions.get(session_id)
        if not session:
            return
        # 找到最近的 permission 事件
        for event in reversed(session.events):
            if event.type == "permission.requested":
                tid = event.payload.get("tool_use_id", "")
                if tid and hasattr(self._event_source, "respond_to_permission"):
                    self._event_source.respond_to_permission(tid, "allow" if approved else "deny")
                session.mark_permission_resolved(tid)
                user_text = "允许" if approved else "拒绝"
                session.add_event(ChatMessage(session_id=session.id, role="user", content=user_text))
                self._push_sessions_to_web()
                break
        # 审批完成后立即缩回 expanded 窗口
        if self.expanded_window.isVisible():
            self.expanded_window.close_to_main()

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._push_sessions_to_web()

    def open_expanded_window(self) -> None:
        if self.expanded_window.isVisible():
            return
        # 暂停主窗口 hover 检测，避免 expanded 打开期间主窗口因鼠标不在上面而收缩
        self._expanded_open = True
        self._hover_timer.stop()
        self._leave_timer.stop()
        self._hover_debounce_timer.stop()
        source_rect = self.geometry()
        self.expanded_window.open_from(source_rect)

    def on_expanded_closed(self) -> None:
        """ExpandedWindow 关闭后恢复主窗口 hover 检测。"""
        self._expanded_open = False
        self._permission_auto_close_timer.stop()
        self._hover_timer.start(100)

    # ------------------------------------------------------------------
    # Hover / Leave
    # ------------------------------------------------------------------

    def _check_hover(self) -> None:
        if self._expanded_open:
            return
        from PySide6.QtGui import QCursor
        widget = QApplication.widgetAt(QCursor.pos())
        inside = widget is not None and (widget is self or self.isAncestorOf(widget))
        if inside:
            self._leave_timer.stop()
            if not self._hovered:
                self.set_hovered(True)
        else:
            if self._hovered and not self._leave_timer.isActive():
                self._leave_timer.start(1000)

    def _on_delayed_leave(self) -> None:
        if self._expanded_open:
            return
        if self._hovered:
            self.set_hovered(False)

    # ------------------------------------------------------------------
    # State changes
    # ------------------------------------------------------------------

    def _on_state_changed(self, state: IslandState) -> None:
        if state == IslandState.IDLE:
            if self._sessions:
                return
            self._sessions.clear()
            self._agents.clear()
        # Web 前端自己管理展开/收起状态，此处无需额外操作

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._event_source.start()
        self.show()

    def stop(self) -> None:
        self._event_source.stop()
        self.close()

    def schedule_cleanup(self) -> None:
        self.cleanup_timer.start(800)

    def compact_memory(self) -> None:
        import gc
        gc.collect()
        self.web_view.page().runJavaScript("if (window.gc) { window.gc(); }")
