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
    resolved_tool_use_ids: set[str] = field(default_factory=set)

    def is_permission_resolved(self, tool_use_id: str) -> bool:
        return tool_use_id in self.resolved_tool_use_ids

    def mark_permission_resolved(self, tool_use_id: str) -> None:
        if tool_use_id:
            self.resolved_tool_use_ids.add(tool_use_id)
        # 所有等待中的权限都已处理，恢复为 running
        if self.status == "needs_attention":
            self.status = "running"

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        if event.type in ("permission.requested", "question.asked"):
            self.status = "needs_attention"
        elif event.type == "session.ended":
            self.status = "completed"
        elif event.type == "progress.updated":
            msg = event.payload.get("message", "")
            # 轮poll检测到的 waiting 状态通过 ProgressUpdated 传递
            if msg.startswith("等待批准"):
                self.status = "needs_attention"
            # 进度更新时，如果之前是 needs_attention，恢复为 running
            elif self.status == "needs_attention":
                self.status = "running"

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
