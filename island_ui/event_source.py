from abc import abstractmethod
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from island_ui.events import (
    Event,
    SessionStarted,
    SessionEnded,
    PermissionRequested,
    QuestionAsked,
    ProgressUpdated,
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
    def __init__(self, interval_ms: int = 3000, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._interval_ms = interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._push_next_event)
        self._script: list[Event] = []
        self._index = 0
        self._build_script()

    def _build_script(self) -> None:
        self._script = [
            SessionStarted(payload={"agent": "Claude Code", "task": "Refactor auth module"}),
            PermissionRequested(action="Edit src/main.py"),
            QuestionAsked(question="Which testing framework should I use?", options=["pytest", "unittest", "nose"]),
            ProgressUpdated(message="Analyzing imports...", percent=30),
            ProgressUpdated(message="Refactoring functions...", percent=70),
            SessionEnded(payload={"status": "completed"}),
        ]

    def start(self) -> None:
        self._index = 0
        self._timer.start(self._interval_ms)
        self._push_next_event()

    def stop(self) -> None:
        self._timer.stop()

    def _push_next_event(self) -> None:
        if self._index >= len(self._script):
            self._timer.stop()
            return
        event = self._script[self._index]
        self._index += 1
        self.event_received.emit(event)

    def reset(self) -> None:
        self._index = 0
        self._build_script()
