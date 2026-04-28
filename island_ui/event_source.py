from abc import abstractmethod
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from island_ui.events import (
    Event,
    SessionStarted,
    SessionEnded,
    PermissionRequested,
    QuestionAsked,
)


class EventSource(QObject):
    event_received = Signal(Event)

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    def inject_event(self, event: Event) -> None:
        self.event_received.emit(event)


class MockEventSource(EventSource):
    """Simulates multiple agent sessions pushing events on a shared timeline."""

    def __init__(self, interval_ms: int = 2500, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._interval_ms = interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._push_next_event)
        self._timeline: list[tuple[float, Event]] = []
        self._index = 0
        self._elapsed = 0.0
        self._build_timeline()

    def _build_timeline(self) -> None:
        """Build a global timeline of events from multiple sessions."""
        s1 = "s1-claude"
        s2 = "s2-codex"
        s3 = "s3-gemini"

        self._timeline = [
            # Session 1: Claude Code
            (0.0, SessionStarted(session_id=s1, payload={"agent": "Claude Code", "task": "fix auth bug"})),
            (2.0, PermissionRequested(session_id=s1, action="Edit src/auth/middleware.ts")),
            (6.0, SessionEnded(session_id=s1, payload={"status": "completed"})),

            # Session 2: Codex
            (3.0, SessionStarted(session_id=s2, payload={"agent": "Codex", "task": "backend server"})),
            (5.0, QuestionAsked(session_id=s2, question="Which deployment target?", options=["Production", "Staging", "Local only"])),
            (9.0, SessionEnded(session_id=s2, payload={"status": "completed"})),

            # Session 3: Gemini
            (6.0, SessionStarted(session_id=s3, payload={"agent": "Gemini", "task": "optimize queries"})),
            (8.0, PermissionRequested(session_id=s3, action="Edit src/db/queries.py")),
            (12.0, SessionEnded(session_id=s3, payload={"status": "completed"})),
        ]

        # Sort by time just in case
        self._timeline.sort(key=lambda x: x[0])

    def start(self) -> None:
        self._index = 0
        self._elapsed = 0.0
        self._timer.start(self._interval_ms)
        self._push_next_event()

    def stop(self) -> None:
        self._timer.stop()

    def _push_next_event(self) -> None:
        if self._index >= len(self._timeline):
            self._timer.stop()
            return

        # Advance elapsed time by one interval step
        self._elapsed += self._interval_ms / 1000.0

        # Emit all events whose time <= elapsed
        while self._index < len(self._timeline) and self._timeline[self._index][0] <= self._elapsed:
            event = self._timeline[self._index][1]
            self._index += 1
            self.event_received.emit(event)

    def reset(self) -> None:
        self._index = 0
        self._elapsed = 0.0
        self._build_timeline()
