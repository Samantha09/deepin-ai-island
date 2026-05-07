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
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "running"  # running, idle, completed, needs_attention
    events: list[Event] = field(default_factory=list)
    resolved_tool_use_ids: set[str] = field(default_factory=set)
    # 终端跳转信息（由 hook 脚本提供）
    tmux_session: str = ""
    tmux_socket: str = ""
    window_id: str = ""
    window_title: str = ""
    terminal_tty: str = ""
    terminal_app: str = ""
    subagents: list[dict] = field(default_factory=list)

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
        self.last_updated = event.timestamp
        if event.type in ("permission.requested", "question.asked"):
            self.status = "needs_attention"
        elif event.type == "session.ended":
            self.status = "completed"
        elif event.type == "progress.updated":
            msg = event.payload.get("message", "")
            poll_status = event.payload.get("status", "")
            # 轮poll检测到的 waiting 状态通过 ProgressUpdated 传递
            if msg.startswith("等待批准"):
                self.status = "needs_attention"
            elif msg == "idle" or poll_status == "idle":
                if self.status != "completed":
                    self.status = "idle"
            elif poll_status in ("processing", "busy"):
                if self.status != "completed":
                    self.status = "running"
            # 进度更新时，如果之前是 needs_attention，恢复为 running
            elif self.status == "needs_attention":
                self.status = "running"

    def last_event(self) -> Optional[Event]:
        return self.events[-1] if self.events else None

    def unresolved_events(self) -> list[Event]:
        return [e for e in self.events if e.type in ("permission.requested", "question.asked")]

    def add_subagent(self, agent_id: str, agent_type: str) -> None:
        """添加或更新活跃子 Agent。"""
        for sa in self.subagents:
            if sa.get("id") == agent_id:
                sa["type"] = agent_type
                sa["started_at"] = datetime.now().timestamp()
                sa.pop("completed_at", None)
                return
        self.subagents.append({
            "id": agent_id,
            "type": agent_type,
            "started_at": datetime.now().timestamp(),
        })

    def remove_subagent(self, agent_id: str) -> None:
        """标记子 Agent 为已完成。"""
        for sa in self.subagents:
            if sa.get("id") == agent_id:
                sa["completed_at"] = datetime.now().timestamp()
                break

    def clear_subagents(self) -> None:
        """清空所有子 Agent（会话结束时调用）。"""
        self.subagents.clear()

    def active_subagents(self) -> list[dict]:
        """返回当前仍在运行的子 Agent 列表。"""
        return [sa for sa in self.subagents if "completed_at" not in sa]

    def duration_text(self) -> str:
        delta = int(datetime.now().timestamp() - self.start_time)
        if delta < 60:
            return f"{delta}s"
        elif delta < 3600:
            return f"{delta // 60}m"
        else:
            return f"{delta // 3600}h"
