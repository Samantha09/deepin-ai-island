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

    def open_from(self, source_rect: QRect) -> None:
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
        QTimer.singleShot(70, self._finish_close_to_main)

    def _finish_close_to_main(self) -> None:
        self.hide()
        self.main_window.raise_()
        self.main_window.activateWindow()
        self._closing = False

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
        self.large_size = (320, 125)
        self.top_margin = 16
        self._hovered = False
        self._native_fixed = False

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

        # 轮询兜底
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
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self._target_rect(width, height))
        self.animation.start()
        self.schedule_cleanup()

    def set_hovered(self, hovered: bool) -> None:
        if self._hovered == hovered:
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
        if session:
            session.add_event(event)

        # 审批事件自动弹开
        if event.type == "permission.requested":
            self._auto_expand_for_permission(event.session_id)

        self._push_sessions_to_web()

    def _auto_expand_for_permission(self, session_id: str) -> None:
        if not self.expanded_window.isVisible():
            self.open_expanded_window()
            self._leave_timer.stop()
            self._leave_timer.start(5000)

    def _push_sessions_to_web(self) -> None:
        import json
        sessions_data = []
        for session in self._sessions.values():
            last_event = session.last_event()
            waiting_action = ""
            if session.status == "needs_attention" and last_event and last_event.type == "permission.requested":
                waiting_action = last_event.payload.get("action", "")
            sessions_data.append({
                "id": session.id,
                "name": session.name,
                "agent": session.agent,
                "status": session.status,
                "waiting_action": waiting_action,
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
        self.expanded_window.update_session_detail(session)
        self.open_expanded_window()

    def respond_permission(self, session_id: str, approved: bool) -> None:
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

    def open_expanded_window(self) -> None:
        if self.expanded_window.isVisible():
            return
        source_rect = self.geometry()
        self.expanded_window.open_from(source_rect)

    # ------------------------------------------------------------------
    # Hover / Leave
    # ------------------------------------------------------------------

    def _check_hover(self) -> None:
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
