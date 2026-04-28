from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QApplication,
)
from PySide6.QtGui import QKeySequence, QShortcut, QColor

from island_ui.compact_pill import CompactPill
from island_ui.expanded_panel import ExpandedPanel
from island_ui.state_machine import IslandStateMachine, IslandState
from island_ui.card_factory import CardFactory
from island_ui.event_source import EventSource
from island_ui.events import Event, SessionStarted, SessionEnded
from island_ui.session import Session


class IslandWindow(QWidget):
    """Floating island window: frameless, always-on-top, solid background."""

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

        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()

    def _setup_window(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().availableGeometry()
        self._max_panel_height = int(screen.height() * 0.6)
        x = screen.x() + (screen.width() - 400) // 2
        self.move(x, screen.y() + 12)

    def _setup_ui(self) -> None:
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#151519"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        self._pill = CompactPill()
        self._pill.setVisible(False)
        self._layout.addWidget(self._pill, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._panel = ExpandedPanel()
        self._panel.setVisible(False)
        self._panel.setFixedHeight(0)
        self._layout.addWidget(self._panel)

        self.setFixedWidth(400)
        self.setMinimumHeight(48)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.timeout.connect(self._on_delayed_leave)

    def _setup_connections(self) -> None:
        self._event_source.event_received.connect(self._on_event)
        self._state_machine.state_changed.connect(self._on_state_changed)
        self._pill.clicked.connect(self._on_pill_clicked)
        self._panel.session_selected.connect(self._on_session_selected)

    def _setup_shortcuts(self) -> None:
        toggle = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        toggle.activated.connect(self._toggle_expand)

        approve = QShortcut(QKeySequence("Ctrl+Y"), self)
        approve.activated.connect(self._approve_first_permission)

        deny = QShortcut(QKeySequence("Ctrl+N"), self)
        deny.activated.connect(self._deny_first_permission)

        esc = QShortcut(QKeySequence("Esc"), self)
        esc.activated.connect(self._on_collapse)

        debug = QShortcut(QKeySequence("Ctrl+D"), self)
        debug.activated.connect(self._inject_test_event)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_event(self, event: Event) -> None:
        self._state_machine.on_event_arrived()

        agent = event.payload.get("agent")
        if agent:
            self._agents.add(agent)

        # Session lifecycle events
        if isinstance(event, SessionStarted):
            session = Session(
                id=event.session_id,
                name=event.payload.get("task", "Untitled"),
                agent=agent or "Unknown",
                terminal=event.payload.get("terminal", "Terminal"),
                start_time=event.timestamp,
            )
            self._sessions[event.session_id] = session
            self._panel.add_session_item(session)
            self._update_pill()
            return

        if isinstance(event, SessionEnded):
            session = self._sessions.get(event.session_id)
            if session:
                session.status = "completed"
                self._panel.update_session_item(session)
            self._update_pill()
            return

        # Regular events: route to session or fallback to global cards
        session = self._sessions.get(event.session_id)
        if session:
            session.add_event(event)
            self._panel.update_session_item(session)

        card = CardFactory.create_card(event, self._panel)
        if card:
            card.resolved.connect(self._on_card_resolved)
            # PermissionCard 有 responded 信号，需要额外连接以支持 socket 回传
            from island_ui.cards.permission_card import PermissionCard
            if isinstance(card, PermissionCard):
                card.responded.connect(self._on_permission_responded)
            self._panel.add_event_card(card)

        self._update_pill()

    def _update_pill(self) -> None:
        # 统计需要注意的会话数（waiting / 有未处理权限请求）
        needs_attention = sum(
            1 for s in self._sessions.values() if s.status == "needs_attention"
        )
        self._pill.set_count(needs_attention)
        self._pill.set_agents(list(self._agents))

    def _on_card_resolved(self, card) -> None:
        self._update_pill()
        if self._panel.unresolved_count() == 0:
            self._state_machine.on_all_resolved()

    def _on_permission_responded(self, response) -> None:
        """当用户在 UI 上点击 Allow/Deny 时，尝试通过 socket 回传给 Claude Code。"""
        sender = self.sender()
        if sender is None:
            return
        tool_use_id = getattr(sender, "tool_use_id", lambda: "")()
        if not tool_use_id:
            return
        decision = "allow" if getattr(response, "approved", False) else "deny"
        if hasattr(self._event_source, "respond_to_permission"):
            self._event_source.respond_to_permission(tool_use_id, decision)

    # ------------------------------------------------------------------
    # Session selection → detail view
    # ------------------------------------------------------------------

    def _on_session_selected(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        self._panel.show_event_detail(session_id, session.name)
        # Add all session events as cards
        for event in session.events:
            card = CardFactory.create_card(event, self._panel)
            if card:
                card.resolved.connect(self._on_card_resolved)
                self._panel.add_event_card(card)

    # ------------------------------------------------------------------
    # User interactions
    # ------------------------------------------------------------------

    def _on_pill_clicked(self) -> None:
        if self._state_machine.state() == IslandState.EXPANDED:
            self._state_machine.on_collapse_requested()
        else:
            self._state_machine.on_expand_requested()

    def _toggle_expand(self) -> None:
        if self._state_machine.state() == IslandState.EXPANDED:
            self._state_machine.on_collapse_requested()
        else:
            self._state_machine.on_expand_requested()

    def _on_collapse(self) -> None:
        self._state_machine.on_collapse_requested()

    def enterEvent(self, event) -> None:
        self._leave_timer.stop()
        if self._state_machine.state() == IslandState.COMPACT:
            self._state_machine.on_expand_requested()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._state_machine.state() == IslandState.EXPANDED:
            self._leave_timer.start(400)
        super().leaveEvent(event)

    def _on_delayed_leave(self) -> None:
        if self._state_machine.state() == IslandState.EXPANDED:
            self._state_machine.on_collapse_requested()

    # ------------------------------------------------------------------
    # State changes → UI updates
    # ------------------------------------------------------------------

    def _on_state_changed(self, state: IslandState) -> None:
        if state == IslandState.IDLE:
            self._set_idle_ui()
        elif state == IslandState.COMPACT:
            self._set_compact_ui()
        elif state == IslandState.EXPANDED:
            self._set_expanded_ui()

    def _set_idle_ui(self) -> None:
        self._pill.setVisible(False)
        self._panel.setVisible(False)
        self._panel.setFixedHeight(0)
        self._panel.clear_cards()
        self._panel.clear_sessions()
        self._agents.clear()
        self._sessions.clear()
        self._resize_to_content()

    def _set_compact_ui(self) -> None:
        self._pill.setVisible(True)
        self._panel.show_session_list()
        self._animate_panel(0, on_finished=lambda: self._panel.setVisible(False))

    def _set_expanded_ui(self) -> None:
        self._pill.setVisible(True)
        self._panel.setVisible(True)
        self._panel.show_session_list()

        content_height = self._panel.sizeHint().height()
        target = min(content_height, self._max_panel_height)
        target = max(target, 120)

        self._animate_panel(target)

    def _animate_panel(self, target_height: int, on_finished=None) -> None:
        if self._panel.height() == target_height:
            if on_finished:
                on_finished()
            self._resize_to_content()
            return

        anim = QPropertyAnimation(self._panel, b"maximumHeight", self)
        anim.setDuration(180)
        anim.setStartValue(self._panel.height())
        anim.setEndValue(target_height)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        def _on_anim_finished():
            self._panel.setFixedHeight(target_height)
            self._resize_to_content()
            if on_finished:
                on_finished()

        anim.finished.connect(_on_anim_finished)
        anim.start()

    def _resize_to_content(self) -> None:
        self._layout.invalidate()
        self._layout.activate()
        self.adjustSize()

    # ------------------------------------------------------------------
    # Shortcuts helpers
    # ------------------------------------------------------------------

    def _approve_first_permission(self) -> None:
        from island_ui.cards.permission_card import PermissionCard
        for card in self._panel.cards():
            if isinstance(card, PermissionCard) and not card.is_resolved():
                card._on_allow()
                return

    def _deny_first_permission(self) -> None:
        from island_ui.cards.permission_card import PermissionCard
        for card in self._panel.cards():
            if isinstance(card, PermissionCard) and not card.is_resolved():
                card._on_deny()
                return

    def _inject_test_event(self) -> None:
        from island_ui.events import PermissionRequested
        event = PermissionRequested(action="Test injection from debug mode")
        self._event_source.inject_event(event)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._event_source.start()
        self.show()

    def stop(self) -> None:
        self._event_source.stop()
        self.close()
