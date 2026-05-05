import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QObject, Signal, Slot, QRect, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtGui import QColor, QIcon, QAction, QPixmap, QPainter

from island_ui.state_machine import IslandStateMachine, IslandState
from island_ui.event_source import EventSource
from island_ui.events import Event, SessionStarted, SessionEnded, ChatMessage
from island_ui.session import Session
from island_ui.plugin import IslandPlugin
from island_ui import plugin_loader


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

    @Slot(str, bool)
    def respondPermissionAll(self, session_id: str, approved: bool) -> None:
        self.window.respond_permission_all(session_id, approved)

    @Slot(str, str)
    def allowAllPermission(self, session_id: str, action: str) -> None:
        self.window.allow_all_permission(session_id, action)

    @Slot(str)
    def closeSession(self, session_id: str) -> None:
        self.window.close_session(session_id)

    @Slot()
    def openExpandedWindow(self) -> None:
        self.window.open_expanded_window()

    @Slot(str)
    def toggleSessionAutoApprove(self, session_id: str) -> None:
        self.window.toggle_session_auto_approve(session_id)

    @Slot(str)
    def jumpToTerminal(self, session_id: str) -> None:
        self.window.jump_to_terminal(session_id)


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

    @Slot(str, bool)
    def respondPermissionAll(self, session_id: str, approved: bool) -> None:
        self.window.main_window.respond_permission_all(session_id, approved)

    @Slot(str, str)
    def allowAllPermission(self, session_id: str, action: str) -> None:
        self.window.main_window.allow_all_permission(session_id, action)


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
        self.large_size = (380, 320)
        self.top_margin = 16
        self._hovered = False
        self._native_fixed = False
        self._expanded_open = False

        # 自动批准配置（规则）
        self._auto_approve = self._load_auto_approve_config()
        # 按会话的自动批准开关状态
        self._session_auto_approve: dict[str, bool] = {}
        # allow-all 规则列表：同类请求自动允许
        self._allow_all_rules: list[dict] = []

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

        # 系统托盘
        self._setup_tray()

        # 插件系统
        self._plugins: list[IslandPlugin] = []

    @staticmethod
    def _load_auto_approve_config() -> dict:
        import yaml
        cfg: dict = {}
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, "config", "default.yaml")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            cfg = data.get("auto_approve", {})
        except Exception:
            pass
        return cfg

    def _should_auto_approve(self, session_id: str, action: str) -> bool:
        """检查会话是否开启了自动批准（开启后所有请求均自动放行）。"""
        return self._session_auto_approve.get(session_id, False)

    def _match_allow_all_rule(self, session_id: str, action: str) -> bool:
        """检查 action 是否命中当前会话的 allow-all 规则。"""
        parts = action.split(":", 1)
        tool = parts[0].strip() if parts else ""
        cmd = parts[1].strip() if len(parts) > 1 else ""
        for rule in self._allow_all_rules:
            if rule.get("session_id") != session_id:
                continue
            if rule.get("tool") != tool:
                continue
            if tool == "Bash":
                cmd_token = cmd.split()[0] if cmd else ""
                if rule.get("cmd_token") == cmd_token:
                    return True
            elif tool in ("Read", "Edit", "Write", "MultiEdit"):
                # 允许所有同类文件操作（不限定具体路径）
                return True
            else:
                if rule.get("pattern") == cmd:
                    return True
        return False

    def allow_all_permission(self, session_id: str, action: str) -> None:
        """允许当前请求，并将当前会话的同类请求加入自动允许规则。"""
        parts = action.split(":", 1)
        tool = parts[0].strip() if parts else ""
        cmd = parts[1].strip() if len(parts) > 1 else ""
        rule: dict = {"session_id": session_id, "tool": tool}
        if tool == "Bash":
            cmd_token = cmd.split()[0] if cmd else ""
            rule["cmd_token"] = cmd_token
        elif tool in ("Read", "Edit", "Write", "MultiEdit"):
            rule["path"] = cmd
        else:
            rule["pattern"] = cmd
        # 去重
        if rule not in self._allow_all_rules:
            self._allow_all_rules.append(rule)

        session = self._sessions.get(session_id)
        if not session:
            return
        # 批量允许当前会话中所有同类的待处理请求
        resolved_any = False
        for event in list(session.events):
            if event.type == "permission.requested":
                event_action = event.payload.get("action", "")
                if self._match_allow_all_rule(session_id, event_action):
                    tid = event.payload.get("tool_use_id", "")
                    if tid and hasattr(self._event_source, "respond_to_permission"):
                        self._event_source.respond_to_permission(tid, "allow")
                    session.mark_permission_resolved(tid)
                    resolved_any = True
        if resolved_any:
            session.add_event(ChatMessage(session_id=session.id, role="user", content="允许所有"))
            self._push_sessions_to_web()
        if self.expanded_window.isVisible():
            self.expanded_window.close_to_main()

    def _auto_respond_permission(self, session: Session, event: Event) -> None:
        tid = event.payload.get("tool_use_id", "")
        if tid and hasattr(self._event_source, "respond_to_permission"):
            self._event_source.respond_to_permission(tid, "allow")
        session.mark_permission_resolved(tid)
        session.add_event(
            ChatMessage(session_id=session.id, role="user", content="自动批准")
        )
        self._push_sessions_to_web()

    def toggle_session_auto_approve(self, session_id: str) -> None:
        current = self._session_auto_approve.get(session_id, False)
        self._session_auto_approve[session_id] = not current
        self._push_sessions_to_web()

    @staticmethod
    def _update_session_terminal(session: Session, payload: dict) -> None:
        """从事件 payload 中更新 session 的终端环境信息。"""
        if payload.get("tmux_session"):
            session.tmux_session = payload["tmux_session"]
        if payload.get("tmux_socket"):
            session.tmux_socket = payload["tmux_socket"]
        if payload.get("window_id"):
            session.window_id = payload["window_id"]
        if payload.get("window_title"):
            session.window_title = payload["window_title"]

    def jump_to_terminal(self, session_id: str) -> None:
        """跳转到会话所在的终端（tmux → 窗口聚焦 → 启动新终端）。"""
        session = self._sessions.get(session_id)
        if not session:
            return
        import shutil
        import subprocess
        # 1. 优先尝试 tmux
        if session.tmux_session:
            tmux_cmd = ["tmux", "switch-client", "-t", session.tmux_session]
            if session.tmux_socket:
                tmux_cmd.insert(1, "-S")
                tmux_cmd.insert(2, session.tmux_socket)
            try:
                subprocess.run(tmux_cmd, check=True, capture_output=True, timeout=3.0)
                return
            except Exception:
                pass
        # 2. 尝试通过窗口 ID 聚焦（xdotool）
        if session.window_id:
            xdotool = shutil.which("xdotool")
            if xdotool:
                try:
                    subprocess.run(
                        [xdotool, "windowactivate", session.window_id],
                        check=True, capture_output=True, timeout=3.0
                    )
                    return
                except Exception:
                    pass
        # 3. 尝试通过窗口标题聚焦（wmctrl 或 xdotool）
        if session.window_title:
            wmctrl = shutil.which("wmctrl")
            if wmctrl:
                try:
                    subprocess.run(
                        [wmctrl, "-a", session.window_title],
                        check=True, capture_output=True, timeout=3.0
                    )
                    return
                except Exception:
                    pass
            xdotool = shutil.which("xdotool")
            if xdotool:
                try:
                    subprocess.run(
                        [xdotool, "search", "--name", session.window_title, "windowactivate"],
                        check=True, capture_output=True, timeout=3.0
                    )
                    return
                except Exception:
                    pass
        # 3.5 通过会话名称或工作目录搜索已有终端窗口
        xdotool = shutil.which("xdotool")
        if xdotool:
            search_terms = []
            if session.name:
                search_terms.append(session.name)
            if session.terminal and session.terminal != os.path.expanduser("~"):
                search_terms.append(os.path.basename(session.terminal))
                search_terms.append(session.terminal)
            for term in search_terms:
                try:
                    result = subprocess.run(
                        [xdotool, "search", "--name", term],
                        capture_output=True, text=True, timeout=3.0
                    )
                    if result.returncode == 0:
                        wids = result.stdout.strip().split()
                        if wids:
                            subprocess.run(
                                [xdotool, "windowactivate", wids[0]],
                                check=True, capture_output=True, timeout=3.0
                            )
                            return
                except Exception:
                    pass

        # 4. 兜底：启动新终端并 cd 到工作目录
        terminal_emulators = [
            "deepin-terminal", "gnome-terminal", "konsole", "alacritty",
            "x-terminal-emulator", "xfce4-terminal", "terminator"
        ]
        for term in terminal_emulators:
            term_path = shutil.which(term)
            if term_path:
                cwd = session.terminal if session.terminal else os.path.expanduser("~")
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen([term_path, "--working-directory", cwd])
                    elif term == "konsole":
                        subprocess.Popen([term_path, "--workdir", cwd])
                    elif term == "alacritty":
                        subprocess.Popen([term_path, "--working-directory", cwd])
                    else:
                        subprocess.Popen([term_path], cwd=cwd)
                    return
                except Exception:
                    pass

    def _target_rect(self, width: int, height: int) -> QRect:
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        x = screen_geo.x() + (screen_geo.width() - width) // 2
        y = screen_geo.y() + self.top_margin
        return QRect(x, y, width, height)

    def animate_to(self, width: int, height: int) -> None:
        current_geo = self.geometry()
        target_y = self._target_rect(width, height).y()
        # 保持水平中心不变，避免宽度变化时视觉左移
        target_x = current_geo.center().x() - width // 2
        target_rect = QRect(target_x, target_y, width, height)
        # 如果已经在目标尺寸，不启动动画
        if current_geo == target_rect:
            return
        # 如果当前动画正在向同一目标运行，不重启动画
        if self.animation.state() == QPropertyAnimation.State.Running and self._anim_target == (width, height):
            return
        self._anim_target = (width, height)
        self.animation.stop()
        self.animation.setStartValue(current_geo)
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

        # 插件事件钩子
        for plugin in self._plugins:
            try:
                plugin.on_event(event)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error("插件 %s on_event 失败: %s", plugin.name, exc)

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
                self._update_session_terminal(session, event.payload)
                self._sessions[event.session_id] = session
                for plugin in self._plugins:
                    try:
                        plugin.on_session_started(session)
                    except Exception as exc:
                        import logging
                        logging.getLogger(__name__).error("插件 %s on_session_started 失败: %s", plugin.name, exc)
            self._push_sessions_to_web()
            return

        if isinstance(event, SessionEnded):
            session = self._sessions.get(event.session_id)
            if session:
                session.status = "completed"
                session.add_event(event)
                for plugin in self._plugins:
                    try:
                        plugin.on_session_ended(session)
                    except Exception as exc:
                        import logging
                        logging.getLogger(__name__).error("插件 %s on_session_ended 失败: %s", plugin.name, exc)
            self._push_sessions_to_web()
            return

        session = self._sessions.get(event.session_id)
        if not session and event.type in ("chat.message", "permission.requested", "question.asked"):
            # 自动恢复被关闭的活跃会话
            fallback_name = event.payload.get("task")
            if not fallback_name:
                cwd = event.payload.get("cwd", event.payload.get("terminal", ""))
                fallback_name = Path(cwd).name if cwd else event.session_id[:8]
            session = Session(
                id=event.session_id,
                name=fallback_name,
                agent=event.payload.get("agent", "Unknown"),
                terminal=event.payload.get("terminal", event.payload.get("cwd", "")),
                start_time=event.timestamp,
            )
            self._update_session_terminal(session, event.payload)
            self._sessions[event.session_id] = session
        if session:
            session.add_event(event)
            # 更新终端环境信息（hook 脚本可能发送了新的 tmux/window 信息）
            self._update_session_terminal(session, event.payload)

        # 审批事件：先插件拦截，再检查自动批准，不满足再弹窗
        if event.type == "permission.requested":
            action = event.payload.get("action", "")
            # 插件权限拦截
            for plugin in self._plugins:
                try:
                    decision = plugin.on_permission_requested(session.id if session else "", action, event)
                    if decision == "allow":
                        if session:
                            self._auto_respond_permission(session, event)
                        self._push_sessions_to_web()
                        return
                    elif decision == "deny":
                        tid = event.payload.get("tool_use_id", "")
                        if tid and hasattr(self._event_source, "respond_to_permission"):
                            self._event_source.respond_to_permission(tid, "deny")
                        if session:
                            session.mark_permission_resolved(tid)
                        self._push_sessions_to_web()
                        return
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).error("插件 %s on_permission_requested 失败: %s", plugin.name, exc)

            # 检查 allow-all 规则（同类请求自动允许）
            if session and self._match_allow_all_rule(session.id, action):
                self._auto_respond_permission(session, event)
                return

            if session and self._should_auto_approve(session.id, action):
                self._auto_respond_permission(session, event)
                return
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
        """从会话事件中提取 1-3 行简短工作概要。"""
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
            elif event.type == "session.started":
                task = event.payload.get("task", "")
                if task:
                    summaries.append(f"任务: {task[:50]}")
            if len(summaries) >= 3:
                break
        if not summaries:
            if session.status == "needs_attention":
                return "等待审批..."
            elif session.status == "running":
                return "运行中..."
            elif session.status == "completed":
                return "已完成"
            else:
                return "准备就绪"
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
            auto_approved = self._session_auto_approve.get(session.id, False)
            sessions_data.append({
                "id": session.id,
                "name": session.name,
                "agent": session.agent,
                "status": session.status,
                "waiting_action": waiting_action,
                "summary": self._build_session_summary(session),
                "auto_approved": auto_approved,
                "tmux_session": session.tmux_session,
                "window_id": session.window_id,
                "window_title": session.window_title,
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
        # 找到最近的未解决 permission 事件
        for event in reversed(session.events):
            if event.type == "permission.requested":
                tid = event.payload.get("tool_use_id", "")
                if not session.is_permission_resolved(tid):
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

    def respond_permission_all(self, session_id: str, approved: bool) -> None:
        """批量响应当前会话所有未解决的权限请求。"""
        self._permission_auto_close_timer.stop()
        session = self._sessions.get(session_id)
        if not session:
            return
        resolved_any = False
        for event in list(session.events):
            if event.type == "permission.requested":
                tid = event.payload.get("tool_use_id", "")
                if not session.is_permission_resolved(tid):
                    if tid and hasattr(self._event_source, "respond_to_permission"):
                        self._event_source.respond_to_permission(tid, "allow" if approved else "deny")
                    session.mark_permission_resolved(tid)
                    resolved_any = True
        if resolved_any:
            user_text = "允许所有" if approved else "拒绝所有"
            session.add_event(ChatMessage(session_id=session.id, role="user", content=user_text))
            self._push_sessions_to_web()
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
        pos = QCursor.pos()
        # 使用窗口几何直接判断，避免 QWebEngine native widget 导致 widgetAt 返回异常
        inside = self.geometry().contains(pos)
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
        # 加载插件
        self._plugins = plugin_loader.load_plugins(self)
        for plugin in self._plugins:
            try:
                plugin.on_ui_ready(self)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error("插件 %s on_ui_ready 失败: %s", plugin.name, exc)

    def stop(self) -> None:
        self._event_source.stop()
        if hasattr(self, "_tray_icon") and self._tray_icon is not None:
            self._tray_icon.hide()
        self.close()

    # ------------------------------------------------------------------
    # System Tray
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        """初始化系统托盘图标和右键菜单。"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self._create_tray_icon())
        self._tray_icon.setToolTip("Deepin AI Island")
        self._tray_icon.activated.connect(self._on_tray_activated)

        menu = QMenu(self)
        show_action = QAction("显示", self)
        show_action.triggered.connect(self._toggle_visibility)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.show()

    def _create_tray_icon(self) -> QIcon:
        """生成一个简单的 tray 图标，不依赖外部文件。"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(202, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 16, 16)
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QApplication.font())
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "AI")
        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_visibility()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
            self.expanded_window.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_app(self) -> None:
        self.stop()
        QApplication.instance().quit()

    def schedule_cleanup(self) -> None:
        self.cleanup_timer.start(800)

    def compact_memory(self) -> None:
        import gc
        gc.collect()
        self.web_view.page().runJavaScript("if (window.gc) { window.gc(); }")
