from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from island_ui.events import Event


@dataclass
class Session:
    id: str
    name: str
    agent: str
    terminal: str
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "running"  # running, completed, needs_attention
    events: list[Event] = field(default_factory=list)

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        if event.type in ("permission.requested", "question.asked"):
            self.status = "needs_attention"
        elif event.type == "session.ended":
            self.status = "completed"

    def last_event(self) -> Optional[Event]:
        return self.events[-1] if self.events else None

    def unresolved_events(self) -> list[Event]:
        return [e for e in self.events if e.type in ("permission.requested", "question.asked")]

    def duration_text(self) -> str:
        delta = int(datetime.now().timestamp() - self.start_time)
        if delta < 60:
            return f"{delta}s"
        elif delta < 3600:
            return f"{delta // 60}m"
        else:
            return f"{delta // 3600}h"
