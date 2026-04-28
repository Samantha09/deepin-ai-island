from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QApplication, QFrame,
)
from PySide6.QtGui import QKeySequence, QShortcut, QPainter, QColor

from island_ui.compact_pill import CompactPill
from island_ui.expanded_panel import ExpandedPanel
from island_ui.state_machine import IslandStateMachine, IslandState
from island_ui.card_factory import CardFactory
from island_ui.event_source import EventSource
from island_ui.events import Event


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
        self.setStyleSheet("background-color: #151519;")

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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#151519"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
        painter.end()

    def _setup_connections(self) -> None:
        self._event_source.event_received.connect(self._on_event)
        self._state_machine.state_changed.connect(self._on_state_changed)
        self._pill.clicked.connect(self._on_pill_clicked)

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
        if self._state_machine.state() == IslandState.COMPACT:
            self._state_machine.on_expand_requested()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._state_machine.state() == IslandState.EXPANDED:
            self._state_machine.on_collapse_requested()
        super().leaveEvent(event)

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
        self._agents.clear()
        self._resize_to_content()

    def _set_compact_ui(self) -> None:
        self._pill.setVisible(True)
        self._animate_panel(0, on_finished=lambda: self._panel.setVisible(False))

    def _set_expanded_ui(self) -> None:
        self._pill.setVisible(True)
        self._panel.setVisible(True)

        content_height = self._panel.sizeHint().height()
        target = min(content_height, self._max_panel_height)
        target = max(target, 120)

        self._animate_panel(target)

    def _animate_panel(self, target_height: int, on_finished=None) -> None:
        anim = QPropertyAnimation(self._panel, b"minimumHeight", self)
        anim.setDuration(250)
        anim.setStartValue(self._panel.height())
        anim.setEndValue(target_height)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

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
