import json
import os
import socket
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread

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


class SocketServerThread(QThread):
    """在后台线程中运行 Unix Socket 服务器，接收 Claude Code hook 事件。"""

    event_received = Signal(dict)
    permission_resolved = Signal(str, str)  # session_id, tool_use_id

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        # tool_use_id -> (client_socket, threading.Event, received_at)
        self._pending: dict[str, tuple[socket.socket, threading.Event, float]] = {}

    def run(self) -> None:
        # 清理旧 socket 文件
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

            # 每个连接单独处理
            handler = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
            handler.start()

        if self._server_sock:
            self._server_sock.close()
            self._server_sock = None

    def stop(self) -> None:
        self._running = False
        # 关闭所有挂起的权限连接
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
        """响应权限请求，写入 socket 并唤醒等待的 handler 线程。"""
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
                # 尝试解析完整 JSON
                try:
                    data = json.loads(b"".join(chunks).decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
            else:
                # 连接关闭且未收到完整 JSON
                client.close()
                return
        except (socket.timeout, OSError):
            client.close()
            return

        # 解析事件
        event_name = data.get("event", "")
        session_id = data.get("session_id", data.get("sessionId", ""))
        tool_use_id = data.get("tool_use_id", data.get("toolUseId", ""))

        if event_name == "PermissionRequest":
            # 需要保持连接等待响应
            event_obj = threading.Event()
            with self._lock:
                self._pending[tool_use_id] = (client, event_obj, time.time())

            # 发射信号到主线程（UI）
            self.event_received.emit(data)

            # 阻塞等待用户决策（最长24小时）
            event_obj.wait(timeout=86400)

            # 如果超时未被响应，清理
            with self._lock:
                if tool_use_id in self._pending:
                    try:
                        client.sendall(json.dumps({"decision": "deny", "reason": "timeout"}).encode("utf-8"))
                        client.close()
                    except OSError:
                        pass
                    self._pending.pop(tool_use_id, None)
        else:
            # 其他事件不需要响应，直接关闭连接
            try:
                client.close()
            except OSError:
                pass
            self.event_received.emit(data)


class ClaudeCodeEventSource(EventSource):
    """通过 Unix Socket 接收 Claude Code hook 事件的 EventSource。

    Claude Code 的 hook 脚本（claude_hooks/ai_island_hook.py）通过
    Unix Domain Socket 将事件实时推送到本类，PermissionRequest 支持双向响应。
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._server = SocketServerThread(self)
        self._server.event_received.connect(self._on_raw_event)
        self._session_names: dict[str, str] = {}

    def start(self) -> None:
        self._session_names.clear()
        if not self._server.isRunning():
            self._server.start()

    def stop(self) -> None:
        self._server.stop()

    def respond_to_permission(self, tool_use_id: str, decision: str, reason: str = "") -> bool:
        """从 UI 响应权限请求。"""
        return self._server.respond_to_permission(tool_use_id, decision, reason)

    def _on_raw_event(self, data: dict) -> None:
        event = self._parse_event(data)
        if event:
            self.event_received.emit(event)

    def _parse_event(self, data: dict) -> Optional[Event]:
        event_name = data.get("event", "")
        session_id = data.get("session_id", data.get("sessionId", ""))
        payload = data.get("payload", {})
        timestamp = data.get("timestamp", time.time())

        # 合并顶层字段到 payload
        for key in ("tool", "tool_input", "tool_use_id", "message", "status", "cwd", "pid", "tty"):
            if key in data:
                payload[key] = data[key]

        if event_name == "SessionStart":
            task = payload.get("prompt", payload.get("task", "Claude Code 会话"))
            self._session_names[session_id] = task
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
                payload={
                    "tool_use_id": payload.get("tool_use_id", ""),
                    **payload,
                },
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

        # 兜底：未知事件也包装为 Event 发出
        return Event(
            type=event_name,
            payload=payload,
            timestamp=timestamp,
            session_id=session_id,
        )

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
