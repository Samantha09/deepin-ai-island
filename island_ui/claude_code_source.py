import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread, QTimer

from island_ui.event_source import EventSource
from island_ui.events import (
    Event,
    SessionStarted,
    SessionEnded,
    PermissionRequested,
    QuestionAsked,
    ProgressUpdated,
)

SOCKET_PATH = "/tmp/ai-island.sock"
SESSIONS_DIR = Path.home() / ".claude" / "sessions"
POLL_INTERVAL_MS = 1500


class SocketServerThread(QThread):
    """在后台线程中运行 Unix Socket 服务器，接收 Claude Code hook 事件。"""

    event_received = Signal(dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[socket.socket, threading.Event, float]] = {}

    def run(self) -> None:
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass

        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o600)
        self._server_sock.listen(10)
        self._server_sock.settimeout(1.0)
        self._running = True

        while self._running:
            try:
                client, _ = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            handler = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
            handler.start()

        if self._server_sock:
            self._server_sock.close()
            self._server_sock = None

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for tool_use_id, (client_sock, event_obj, _) in list(self._pending.items()):
                try:
                    client_sock.close()
                except OSError:
                    pass
                event_obj.set()
            self._pending.clear()
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
        self.wait(3000)

    def respond_to_permission(self, tool_use_id: str, decision: str, reason: str = "") -> bool:
        with self._lock:
            pending = self._pending.get(tool_use_id)
            if pending is None:
                return False
            client_sock, event_obj, _ = pending

        response = {"decision": decision}
        if reason:
            response["reason"] = reason
        try:
            data = json.dumps(response, ensure_ascii=False).encode("utf-8")
            client_sock.sendall(data)
            client_sock.close()
        except OSError:
            pass
        finally:
            event_obj.set()
            with self._lock:
                self._pending.pop(tool_use_id, None)
        return True

    def _handle_client(self, client: socket.socket) -> None:
        try:
            client.settimeout(5.0)
            chunks = []
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    data = json.loads(b"".join(chunks).decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
            else:
                client.close()
                return
        except (socket.timeout, OSError):
            client.close()
            return

        event_name = data.get("event", "")
        tool_use_id = data.get("tool_use_id", data.get("toolUseId", ""))

        if event_name == "PermissionRequest" and tool_use_id:
            event_obj = threading.Event()
            with self._lock:
                self._pending[tool_use_id] = (client, event_obj, time.time())
            self.event_received.emit(data)
            event_obj.wait(timeout=86400)
            with self._lock:
                if tool_use_id in self._pending:
                    try:
                        client.sendall(json.dumps({"decision": "deny", "reason": "timeout"}).encode("utf-8"))
                        client.close()
                    except OSError:
                        pass
                    self._pending.pop(tool_use_id, None)
        else:
            try:
                client.close()
            except OSError:
                pass
            self.event_received.emit(data)


class ClaudeCodeEventSource(EventSource):
    """Claude Code 事件源：Unix Socket + 会话文件轮询。

    同时通过两种机制获取事件：
    1. Unix Socket：接收 hook 实时推送的事件，支持 PermissionRequest 双向响应
    2. 轮询 ~/.claude/sessions/*.json：主动发现所有活跃会话及状态变化
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._server = SocketServerThread(self)
        self._server.event_received.connect(self._on_raw_event)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_sessions)

        # 已知的 session 状态：session_id -> {"status": ..., "cwd": ..., "waitingFor": ...}
        self._known_sessions: dict[str, dict] = {}

    def start(self) -> None:
        self._known_sessions.clear()
        if not self._server.isRunning():
            self._server.start()
        self._poll_timer.start(POLL_INTERVAL_MS)
        self._poll_sessions()

    def stop(self) -> None:
        self._poll_timer.stop()
        self._server.stop()

    def respond_to_permission(self, tool_use_id: str, decision: str, reason: str = "") -> bool:
        return self._server.respond_to_permission(tool_use_id, decision, reason)

    # ------------------------------------------------------------------
    # Session 文件轮询
    # ------------------------------------------------------------------

    def _poll_sessions(self) -> None:
        """扫描 ~/.claude/sessions/*.json，发现新会话和状态变化。"""
        if not SESSIONS_DIR.exists():
            return

        current_ids: set[str] = set()

        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            session_id = data.get("sessionId", "")
            if not session_id:
                continue

            current_ids.add(session_id)
            status = data.get("status", "")
            cwd = data.get("cwd", "")
            waiting_for = data.get("waitingFor", "")

            known = self._known_sessions.get(session_id)

            if known is None:
                # 新会话
                self._known_sessions[session_id] = {
                    "status": status,
                    "cwd": cwd,
                    "waitingFor": waiting_for,
                }
                self._emit_session_started(session_id, cwd)
            else:
                # 已有会话，检查状态变化
                old_status = known.get("status")
                old_waiting = known.get("waitingFor", "")

                if status != old_status or waiting_for != old_waiting:
                    known["status"] = status
                    known["cwd"] = cwd
                    known["waitingFor"] = waiting_for
                    self._handle_status_change(session_id, status, waiting_for, cwd)

        # 检测已消失的会话
        for session_id in list(self._known_sessions.keys()):
            if session_id not in current_ids:
                del self._known_sessions[session_id]
                self.event_received.emit(
                    SessionEnded(session_id=session_id, payload={"status": "completed"})
                )

    def _emit_session_started(self, session_id: str, cwd: str) -> None:
        task = f"Claude Code @ {Path(cwd).name if cwd else 'Unknown'}"
        event = SessionStarted(
            session_id=session_id,
            payload={
                "agent": "Claude Code",
                "task": task,
                "terminal": cwd,
            },
        )
        self.event_received.emit(event)

    def _handle_status_change(self, session_id: str, status: str, waiting_for: str, cwd: str) -> None:
        if status == "waiting" and waiting_for:
            # 解析 waitingFor，例如 "approve Bash"、"approve Write"
            action = waiting_for
            if waiting_for.startswith("approve "):
                action = waiting_for[8:]  # 去掉 "approve "
            event = PermissionRequested(
                session_id=session_id,
                action=action,
                payload={"waitingFor": waiting_for, "cwd": cwd},
            )
            self.event_received.emit(event)
        elif status in ("busy", "running_tool", "processing"):
            event = ProgressUpdated(
                session_id=session_id,
                message=f"状态: {status}",
                payload={"status": status, "cwd": cwd},
            )
            self.event_received.emit(event)
        elif status == "idle":
            event = ProgressUpdated(
                session_id=session_id,
                message="空闲中",
                payload={"status": status, "cwd": cwd},
            )
            self.event_received.emit(event)

    # ------------------------------------------------------------------
    # Socket 事件解析
    # ------------------------------------------------------------------

    def _on_raw_event(self, data: dict) -> None:
        event = self._parse_socket_event(data)
        if event:
            self.event_received.emit(event)

    def _parse_socket_event(self, data: dict) -> Optional[Event]:
        event_name = data.get("event", "")
        session_id = data.get("session_id", data.get("sessionId", ""))
        payload = data.get("payload", {})
        timestamp = data.get("timestamp", time.time())

        for key in ("tool", "tool_input", "tool_use_id", "message", "status", "cwd", "pid", "tty"):
            if key in data:
                payload[key] = data[key]

        if event_name == "SessionStart":
            task = payload.get("prompt", payload.get("task", "Claude Code 会话"))
            return SessionStarted(
                session_id=session_id,
                payload={
                    "agent": "Claude Code",
                    "task": task,
                    "terminal": payload.get("cwd", ""),
                    **{k: v for k, v in payload.items() if k not in ("agent", "task", "terminal")},
                },
                timestamp=timestamp,
            )

        if event_name == "SessionEnd":
            return SessionEnded(
                session_id=session_id,
                payload={"status": "completed", **payload},
                timestamp=timestamp,
            )

        if event_name == "PermissionRequest":
            tool = payload.get("tool", "Unknown")
            tool_input = payload.get("tool_input", {})
            action = self._format_action(tool, tool_input)
            return PermissionRequested(
                session_id=session_id,
                action=action,
                payload={"tool_use_id": payload.get("tool_use_id", ""), **payload},
                timestamp=timestamp,
            )

        if event_name == "PreToolUse":
            tool = payload.get("tool", "Unknown")
            tool_input = payload.get("tool_input", {})
            action = self._format_action(tool, tool_input)
            return PermissionRequested(
                session_id=session_id,
                action=action,
                payload=payload,
                timestamp=timestamp,
            )

        if event_name == "PostToolUse":
            tool = payload.get("tool", "Unknown")
            return ProgressUpdated(
                session_id=session_id,
                message=f"已完成: {tool}",
                payload=payload,
                timestamp=timestamp,
            )

        if event_name == "UserPromptSubmit":
            prompt = payload.get("prompt", "")
            return QuestionAsked(
                session_id=session_id,
                question=prompt,
                payload=payload,
                timestamp=timestamp,
            )

        if event_name == "Stop":
            return SessionEnded(
                session_id=session_id,
                payload={"status": "completed", **payload},
                timestamp=timestamp,
            )

        return Event(type=event_name, payload=payload, timestamp=timestamp, session_id=session_id)

    @staticmethod
    def _format_action(tool: str, tool_input: dict) -> str:
        if tool == "Bash":
            cmd = tool_input.get("command", "")
            return f"Bash: {cmd[:80]}"
        if tool in ("Edit", "Write", "MultiEdit"):
            path = tool_input.get("path", tool_input.get("file_path", ""))
            return f"{tool}: {path}"
        if tool == "Read":
            path = tool_input.get("path", "")
            return f"Read: {path}"
        return tool
