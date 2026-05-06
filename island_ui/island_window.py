import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QVariantAnimation, QEasingCurve, QTimer, QObject, Signal, Slot, QRect, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtGui import QColor, QIcon, QAction, QPixmap, QPainter, QRegion

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

    @Slot()
    def clearCompletedSessions(self) -> None:
        self.window.clear_completed_sessions()

    @Slot(bool)
    def setSoundEnabled(self, enabled: bool) -> None:
        self.window.set_sound_enabled(enabled)

    @Slot(int)
    def setSoundVolume(self, volume: int) -> None:
        self.window.set_sound_volume(volume)

    @Slot()
    def quitApp(self) -> None:
        self.window.quit_app()


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
        # 已完成的会话自动变灰定时器
        self._completed_timers: dict[str, QTimer] = {}

        self.small_size = (320, 45)
        self.large_size = (380, 320)
        self.top_margin = 16
        self._hovered = False
        self._native_fixed = False
        self._expanded_open = False
        self._permission_notify_expanded = False

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
        self.web_view.loadFinished.connect(self._on_web_load_finished)

        self.expanded_window = ExpandedWindow(self)

        # 窗口始终固定为 large_size，通过 setMask 控制可见高度来实现展开/收起。
        # 这样可以完全避免 QWebEngineView 的逐帧 resize，彻底消除抖动。
        self.setFixedSize(*self.large_size)
        self.web_view.setFixedSize(*self.large_size)
        initial_rect = self._target_rect(*self.large_size)
        self.move(initial_rect.x(), initial_rect.y())
        self._mask_height = self.small_size[1]
        self.setMask(QRegion(0, 0, self.large_size[0], self._mask_height))

        # Mask 高度动画（展开/收起）
        self._mask_anim = QVariantAnimation(self)
        self._mask_anim.setDuration(400)
        self._mask_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._mask_anim.valueChanged.connect(self._on_mask_value_changed)

        self._anim_target: Optional[tuple[int, int]] = None

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
        if payload.get("terminal_tty"):
            session.terminal_tty = payload["terminal_tty"]
        if payload.get("terminal_app"):
            session.terminal_app = payload["terminal_app"]

    def jump_to_terminal(self, session_id: str) -> None:
        """跳转到会话所在的终端（tmux → TTY+进程树 → terminal_app → window_id）。"""
        session = self._sessions.get(session_id)
        if not session:
            self._log_jump(session_id, "session not found")
            return
        import shutil
        import subprocess

        xdotool = shutil.which("xdotool")
        tmux_bin = shutil.which("tmux")

        # 1. tmux: 找到活跃客户端的 TTY 或 pane TTY，然后激活对应窗口
        if session.tmux_session and tmux_bin:
            self._log_jump(session_id, f"tmux_session={session.tmux_session}")
            socket_args = []
            if session.tmux_socket:
                socket_args = ["-S", session.tmux_socket]

            # 方法A: 获取活跃客户端的 TTY，找到对应终端窗口
            try:
                result = subprocess.run(
                    [tmux_bin] + socket_args + ["list-clients", "-t", session.tmux_session, "-F", "#{client_tty}"],
                    capture_output=True, text=True, timeout=2.0
                )
                if result.returncode == 0:
                    client_ttys = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
                    self._log_jump(session_id, f"tmux clients: {client_ttys}")
                    for tty in client_ttys:
                        if self._activate_by_tty(tty, session_id, xdotool):
                            return
                else:
                    self._log_jump(session_id, f"tmux list-clients rc={result.returncode}")
            except Exception as e:
                self._log_jump(session_id, f"tmux client lookup exception: {e}")

            # 方法B: 获取 pane TTY 作为 fallback
            try:
                result = subprocess.run(
                    [tmux_bin] + socket_args + ["list-panes", "-t", session.tmux_session, "-F", "#{pane_tty}"],
                    capture_output=True, text=True, timeout=2.0
                )
                if result.returncode == 0:
                    pane_ttys = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
                    self._log_jump(session_id, f"tmux pane ttys: {pane_ttys}")
                    for tty in pane_ttys:
                        if self._activate_by_tty(tty, session_id, xdotool):
                            return
            except Exception as e:
                self._log_jump(session_id, f"tmux pane lookup exception: {e}")
        else:
            if session.tmux_session:
                self._log_jump(session_id, "tmux_session set but tmux binary not found")
            else:
                self._log_jump(session_id, "no tmux_session")

        # 2. 通过 TTY → 进程树向上遍历 → 找到有 X11 窗口的祖先进程
        if session.terminal_tty and xdotool:
            if self._activate_by_tty(session.terminal_tty, session_id, xdotool):
                return
        elif not session.terminal_tty:
            self._log_jump(session_id, "no terminal_tty")

        # 3. 通过 terminal_app 类名搜索窗口并激活
        if session.terminal_app and xdotool:
            self._log_jump(session_id, f"terminal_app={session.terminal_app!r}, trying class search")
            try:
                class_candidates = []
                app_lower = session.terminal_app.lower()
                if "pycharm" in app_lower:
                    class_candidates = ["jetbrains-pycharm", "pycharm"]
                elif "vscode" in app_lower or "code" in app_lower:
                    class_candidates = ["code", "vscode"]
                elif "deepin-terminal" in app_lower:
                    class_candidates = ["deepin-terminal", "terminal"]
                elif "gnome-terminal" in app_lower:
                    class_candidates = ["gnome-terminal", "terminal"]
                elif "konsole" in app_lower:
                    class_candidates = ["konsole"]
                else:
                    class_candidates = [app_lower]

                for cls in class_candidates:
                    r = subprocess.run(
                        [xdotool, "search", "--onlyvisible", "--class", cls],
                        capture_output=True, text=True, timeout=3.0
                    )
                    if r.returncode == 0:
                        wids = r.stdout.strip().split()
                        if wids:
                            best = self._pick_best_window(wids, session_id)
                            subprocess.run(
                                [xdotool, "windowactivate", best],
                                check=True, capture_output=True, timeout=3.0
                            )
                            self._log_jump(session_id, f"class search OK: class={cls}, window={best}")
                            return
            except Exception as e:
                self._log_jump(session_id, f"class search exception: {e}")

        # 4. 尝试通过窗口 ID 聚焦
        self._log_jump(session_id, f"window_id={session.window_id!r}")
        if session.window_id and xdotool:
            try:
                subprocess.run(
                    [xdotool, "windowactivate", session.window_id],
                    check=True, capture_output=True, timeout=3.0
                )
                self._log_jump(session_id, f"windowactivate {session.window_id} OK")
                return
            except Exception as e:
                self._log_jump(session_id, f"windowactivate FAIL: {e}")
        self._log_jump(session_id, "all methods exhausted")

    def _activate_by_tty(self, tty: str, session_id: str, xdotool: Optional[str]) -> bool:
        """通过 TTY 找到对应的终端窗口并激活。返回是否成功。"""
        import subprocess
        if not xdotool:
            return False
        try:
            result = subprocess.run(
                ["ps", "-t", tty, "-o", "pid=", "--no-headers"],
                capture_output=True, text=True, timeout=3.0
            )
            if result.returncode != 0:
                self._log_jump(session_id, f"ps -t {tty} rc={result.returncode}")
                return False
            pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            for pid in pids:
                current_pid = pid
                for _ in range(16):
                    ppid_result = subprocess.run(
                        ["ps", "-o", "ppid=", "-p", str(current_pid)],
                        capture_output=True, text=True, timeout=1.0
                    )
                    if ppid_result.returncode != 0:
                        break
                    ppid = ppid_result.stdout.strip()
                    if not ppid or ppid in ("0", "1"):
                        break
                    wid_result = subprocess.run(
                        [xdotool, "search", "--onlyvisible", "--pid", ppid],
                        capture_output=True, text=True, timeout=1.0
                    )
                    if wid_result.returncode == 0:
                        wids = wid_result.stdout.strip().split()
                        if wids:
                            best = self._pick_best_window(wids, session_id)
                            subprocess.run(
                                [xdotool, "windowactivate", best],
                                check=True, capture_output=True, timeout=3.0
                            )
                            self._log_jump(session_id, f"tty OK: tty={tty}, pid={ppid}, window={best}")
                            return True
                    current_pid = ppid
        except Exception as e:
            self._log_jump(session_id, f"tty activate exception: {e}")
        return False

    def _pick_best_window(self, wids: list[str], session_id: str) -> str:
        """从多个窗口中选择最可能匹配当前会话的窗口（通过 CWD 匹配标题）。"""
        import subprocess
        import os
        if len(wids) <= 1:
            return wids[0] if wids else ""
        session = self._sessions.get(session_id)
        if not session:
            return wids[0]
        # 提取会话的 CWD
        cwd = ""
        for event in reversed(session.events):
            cwd = event.payload.get("cwd", "")
            if cwd:
                break
        if not cwd:
            return wids[0]
        cwd_name = os.path.basename(cwd).lower()
        if not cwd_name:
            return wids[0]
        # 获取每个窗口的标题，尝试匹配
        for wid in wids:
            try:
                result = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=1.0
                )
                if result.returncode == 0:
                    title = result.stdout.strip().lower()
                    if cwd_name in title:
                        return wid
            except Exception:
                pass
        return wids[0]

    def _log_jump(self, session_id: str, message: str) -> None:
        try:
            with open("/tmp/ai-island-jump.log", "a", encoding="utf-8") as f:
                f.write(f"[{session_id}] {message}\n")
        except Exception:
            pass

    def _target_rect(self, width: int, height: int) -> QRect:
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        x = screen_geo.x() + (screen_geo.width() - width) // 2
        y = screen_geo.y() + self.top_margin
        return QRect(x, y, width, height)

    def _on_mask_value_changed(self, height: int) -> None:
        self.setMask(QRegion(0, 0, self.large_size[0], int(height)))

    def set_mask_height(self, height: int) -> None:
        if self._mask_anim.state() == QVariantAnimation.State.Running:
            self._mask_anim.stop()
        self._mask_anim.setStartValue(self._mask_height)
        self._mask_anim.setEndValue(height)
        self._mask_anim.start()
        self._mask_height = height
        self.schedule_cleanup()

    def animate_to(self, width: int, height: int) -> None:
        """兼容旧接口，实际通过 mask 高度控制展开/收起。"""
        if height == self.large_size[1]:
            self.set_mask_height(self.large_size[1])
        else:
            self.set_mask_height(self.small_size[1])

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
                # 30 秒后自动将 completed 变为 idle
                self._schedule_completed_expire(event.session_id)
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
            # 任何会话状态变化都推送到前端，确保列表及时刷新
            self._push_sessions_to_web()

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
            # 审批到达时自动触发悬停展开效果（显示会话列表而非详情页），5s 后自动收回
            self._auto_expand_for_permission()

        self._push_sessions_to_web()

    def _auto_expand_for_permission(self) -> None:
        if not self._permission_notify_expanded:
            self._permission_notify_expanded = True
            self.animate_to(*self.large_size)
            self.web_view.page().runJavaScript(
                "if (typeof window.setNotificationExpand === 'function') { window.setNotificationExpand(true); }"
            )
            self._permission_auto_close_timer.stop()
            self._permission_auto_close_timer.start(5000)

    def _on_permission_auto_close(self) -> None:
        if self._permission_notify_expanded:
            self._permission_notify_expanded = False
            self.animate_to(*self.small_size)
            self.web_view.page().runJavaScript(
                "if (typeof window.setNotificationExpand === 'function') { window.setNotificationExpand(false); }"
            )

    def _build_session_summary(self, session: Session) -> list[str]:
        """从会话事件中提取 1-3 行简短工作概要，返回列表以便前端逐行渲染对话效果。"""
        summaries: list[str] = []
        for event in reversed(session.events):
            if event.type == "chat.message":
                content = event.payload.get("content", "")
                role = event.payload.get("role", "assistant")
                prefix = "你" if role == "user" else "AI"
                text = content[:80] + "..." if len(content) > 80 else content
                summaries.append(f"{prefix}: {text}")
            elif event.type == "permission.requested":
                action = event.payload.get("action", "")
                text = action[:80] + "..." if len(action) > 80 else action
                summaries.append(f"需要审批: {text}")
            elif event.type == "progress.updated":
                msg = event.payload.get("message", "")
                if msg and msg != "idle":
                    summaries.append(msg[:80])
            elif event.type == "session.started":
                task = event.payload.get("task", "")
                if task:
                    summaries.append(f"任务: {task[:80]}")
            if len(summaries) >= 3:
                break
        if not summaries:
            if session.status == "needs_attention":
                return ["等待审批..."]
            elif session.status == "running":
                return ["运行中..."]
            elif session.status == "completed":
                return ["已完成"]
            else:
                return ["准备就绪"]
        return list(reversed(summaries))

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

    def _on_web_load_finished(self, ok: bool) -> None:
        """页面加载完成后推送一次会话列表，确保首次启动时能正确显示。"""
        if ok:
            self._push_sessions_to_web()

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

    def _schedule_completed_expire(self, session_id: str) -> None:
        """已完成的会话 30 秒后自动变为 idle（灰色）。"""
        # 取消已有定时器
        old_timer = self._completed_timers.pop(session_id, None)
        if old_timer is not None:
            old_timer.stop()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._expire_completed_session(session_id))
        timer.start(30000)
        self._completed_timers[session_id] = timer

    def _expire_completed_session(self, session_id: str) -> None:
        """将会话从 completed 变为 idle。"""
        self._completed_timers.pop(session_id, None)
        session = self._sessions.get(session_id)
        if session and session.status == "completed":
            session.status = "idle"
            self._push_sessions_to_web()

    def close_session(self, session_id: str) -> None:
        # 取消 completed 定时器
        old_timer = self._completed_timers.pop(session_id, None)
        if old_timer is not None:
            old_timer.stop()
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
        # 如果之前处于权限通知自动展开状态，需要清理，否则 Island 会永远展开
        if self._permission_notify_expanded:
            self._permission_notify_expanded = False
            self.web_view.page().runJavaScript(
                "if (typeof window.setNotificationExpand === 'function') { window.setNotificationExpand(false); }"
            )
        self._hover_timer.start(100)

    # ------------------------------------------------------------------
    # Hover / Leave
    # ------------------------------------------------------------------

    def _check_hover(self) -> None:
        if self._expanded_open or self._permission_notify_expanded:
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
        if self._permission_notify_expanded:
            # 鼠标移开后强制清除权限通知展开状态，避免永远展开
            self._permission_notify_expanded = False
            self._permission_auto_close_timer.stop()
            self.animate_to(*self.small_size)
            self.web_view.page().runJavaScript(
                "if (typeof window.setNotificationExpand === 'function') { window.setNotificationExpand(false); }"
            )
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
        # 启动后延迟推送一次会话列表，确保已有会话被加载到前端
        QTimer.singleShot(300, self._push_sessions_to_web)
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

    def clear_completed_sessions(self) -> None:
        """移除所有 completed 或 idle 状态的会话。"""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.status in ("completed", "idle")
        ]
        for sid in to_remove:
            old_timer = self._completed_timers.pop(sid, None)
            if old_timer is not None:
                old_timer.stop()
            self._sessions.pop(sid, None)
        if to_remove:
            self._push_sessions_to_web()

    def set_sound_enabled(self, enabled: bool) -> None:
        """设置音效开关。"""
        if self._config_manager is not None:
            self._config_manager.set("sound.enabled", bool(enabled))

    def set_sound_volume(self, volume: int) -> None:
        """设置音效音量（0-100）。"""
        if self._config_manager is not None:
            self._config_manager.set("sound.volume", max(0, min(100, int(volume))))

    def quit_app(self) -> None:
        """退出应用。"""
        QApplication.instance().quit()
