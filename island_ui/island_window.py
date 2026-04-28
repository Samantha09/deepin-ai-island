from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication,
)
from PySide6.QtGui import QKeySequence, QShortcut

from island_ui.compact_pill import CompactPill
from island_ui.expanded_panel import ExpandedPanel
from island_ui.state_machine import IslandStateMachine, IslandState
from island_ui.card_factory import CardFactory
from island_ui.event_source import EventSource
from island_ui.events import Event
class IslandWindow(QMainWindow):
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

        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()

    def _setup_window(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        # Prevent stealing focus on show, but allow child widgets to receive focus
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Position at top-center of primary screen
        screen = QApplication.primaryScreen().geometry()
        width = 420
        self.setFixedWidth(width)
        x = (screen.width() - width) // 2
        self.move(x, 12)

    def _setup_ui(self) -> None:
        self._central = QWidget()
        self._central.setStyleSheet("background: transparent;")
        self.setCentralWidget(self._central)

        self._layout = QVBoxLayout(self._central)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self._pill = CompactPill()
        self._pill.setVisible(False)
        self._layout.addWidget(self._pill)

        self._panel = ExpandedPanel()
        self._panel.setVisible(False)
        self._layout.addWidget(self._panel)

    def _setup_connections(self) -> None:
        self._event_source.event_received.connect(self._on_event)
        self._state_machine.state_changed.connect(self._on_state_changed)
        self._pill.clicked.connect(self._on_pill_clicked)

    def _setup_shortcuts(self) -> None:
        # Ctrl+Shift+I: toggle expand/collapse
        toggle = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        toggle.activated.connect(self._toggle_expand)

        # Ctrl+Y: approve first pending permission
        approve = QShortcut(QKeySequence("Ctrl+Y"), self)
        approve.activated.connect(self._approve_first_permission)

        # Ctrl+N: deny first pending permission
        deny = QShortcut(QKeySequence("Ctrl+N"), self)
        deny.activated.connect(self._deny_first_permission)

        # Esc: collapse
        esc = QShortcut(QKeySequence("Esc"), self)
        esc.activated.connect(self._on_collapse)

        # Ctrl+D: inject test event
        debug = QShortcut(QKeySequence("Ctrl+D"), self)
        debug.activated.connect(self._inject_test_event)

    def _on_event(self, event: Event) -> None:
        self._state_machine.on_event_arrived()

        # Update agents tracking
        agent = event.payload.get("agent")
        if agent:
            self._agents.add(agent)

        card = CardFactory.create_card(event, self._panel)
        if card:
            card.resolved.connect(self._on_card_resolved)
            self._panel.add_card(card)

        self._update_pill()

    def _update_pill(self) -> None:
        unresolved = self._panel.unresolved_count()
        self._pill.set_count(unresolved)
        self._pill.set_agents(list(self._agents))

    def _on_card_resolved(self, card) -> None:
        self._update_pill()
        if self._panel.unresolved_count() == 0:
            self._state_machine.on_all_resolved()

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

    def enterEvent(self, event) -> None:
        if self._state_machine.state() == IslandState.COMPACT:
            self._state_machine.on_expand_requested()
        super().enterEvent(event)

    def _on_collapse(self) -> None:
        self._state_machine.on_collapse_requested()

    def _on_state_changed(self, state: IslandState) -> None:
        if state == IslandState.IDLE:
            self._pill.setVisible(False)
            self._panel.setVisible(False)
            self._panel.setMaximumHeight(0)
            self._panel.clear_cards()
            self._agents.clear()
        elif state == IslandState.COMPACT:
            self._pill.setVisible(True)
            self._animate_panel_height(0, lambda: self._panel.setVisible(False))
        elif state == IslandState.EXPANDED:
            self._pill.setVisible(True)
            self._panel.setVisible(True)
            target = int(QApplication.primaryScreen().geometry().height() * 0.6)
            self._panel.setMaximumHeight(target)

    def _animate_panel_height(self, target_height: int, on_finished=None) -> None:
        anim = QPropertyAnimation(self._panel, b"maximumHeight", self)
        anim.setDuration(250)
        anim.setStartValue(self._panel.maximumHeight())
        anim.setEndValue(target_height)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()

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

    def start(self) -> None:
        self._event_source.start()
        self.show()

    def stop(self) -> None:
        self._event_source.stop()
        self.close()
