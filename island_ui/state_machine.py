from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer


class IslandState(Enum):
    IDLE = auto()
    COMPACT = auto()
    EXPANDED = auto()


class IslandStateMachine(QObject):
    state_changed = Signal(IslandState)

    def __init__(self, compact_timeout_ms: int = 5000, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._state = IslandState.IDLE
        self._compact_timeout_ms = compact_timeout_ms
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_idle_timeout)

    def state(self) -> IslandState:
        return self._state

    def _transition(self, new_state: IslandState) -> None:
        if self._state == new_state:
            return
        self._state = new_state
        self.state_changed.emit(new_state)

    def on_event_arrived(self) -> None:
        self._idle_timer.stop()
        if self._state == IslandState.IDLE:
            self._transition(IslandState.COMPACT)

    def on_expand_requested(self) -> None:
        self._idle_timer.stop()
        if self._state in (IslandState.IDLE, IslandState.COMPACT):
            self._transition(IslandState.EXPANDED)

    def on_collapse_requested(self) -> None:
        self._idle_timer.stop()
        if self._state == IslandState.EXPANDED:
            self._transition(IslandState.COMPACT)
            self._idle_timer.start(self._compact_timeout_ms)

    def on_all_resolved(self) -> None:
        if self._state == IslandState.EXPANDED:
            self._transition(IslandState.COMPACT)
            self._idle_timer.start(self._compact_timeout_ms)

    def _on_idle_timeout(self) -> None:
        if self._state == IslandState.COMPACT:
            self._transition(IslandState.IDLE)
