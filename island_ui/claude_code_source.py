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
        # PreToolUse -> PermissionRequest tool_use_id 缓存
        self._tool_use_id_cache: dict[str, list[str]] = {}
        self._cache_lock = threading.Lock()

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

    # ------------------------------------------------------------------
    # Tool Use ID Cache (PreToolUse -> PermissionRequest correlation)
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(session_id: str, tool_name: str, tool_input: dict) -> str:
        input_str = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
        return f"{session_id}:{tool_name}:{input_str}"

    def _cache_tool_use_id(self, session_id: str, tool_name: str, tool_input: dict, tool_use_id: str) -> None:
        key = self._cache_key(session_id, tool_name, tool_input)
        with self._cache_lock:
            if key not in self._tool_use_id_cache:
                self._tool_use_id_cache[key] = []
            self._tool_use_id_cache[key].append(tool_use_id)

    def _pop_cached_tool_use_id(self, session_id: str, tool_name: str, tool_input: dict) -> Optional[str]:
        key = self._cache_key(session_id, tool_name, tool_input)
        with self._cache_lock:
            queue = self._tool_use_id_cache.get(key)
            if not queue:
                return None
            tool_use_id = queue.pop(0)
            if not queue:
                del self._tool_use_id_cache[key]
            else:
                self._tool_use_id_cache[key] = queue
            return tool_use_id

    def _cleanup_cache(self, session_id: str) -> None:
        with self._cache_lock:
            keys_to_remove = [k for k in self._tool_use_id_cache if k.startswith(f"{session_id}:")]
            for k in keys_to_remove:
                del self._tool_use_id_cache[k]

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
        if not event_name:
            event_name = data.get("hook_event_name", "")
        session_id = data.get("session_id", data.get("sessionId", ""))
        tool_use_id = data.get("tool_use_id", data.get("toolUseId", ""))
        tool_name = data.get("tool_name", data.get("tool", ""))
        tool_input = data.get("tool_input", data.get("toolInput", {}))

        # Cache tool_use_id from PreToolUse for PermissionRequest correlation
        if event_name == "PreToolUse" and tool_use_id:
            self._cache_tool_use_id(session_id, tool_name, tool_input, tool_use_id)
            client.close()
            self.event_received.emit(data)
            return

        if event_name == "SessionEnd":
            self._cleanup_cache(session_id)

        if event_name == "PermissionRequest":
            # PermissionRequest often does NOT include tool_use_id, retrieve from cache
            resolved_tool_use_id = tool_use_id
            if not resolved_tool_use_id:
                resolved_tool_use_id = self._pop_cached_tool_use_id(session_id, tool_name, tool_input)

            if resolved_tool_use_id:
                # Inject resolved tool_use_id back into data so parser can use it
                data["tool_use_id"] = resolved_tool_use_id
                event_obj = threading.Event()
                with self._lock:
                    self._pending[resolved_tool_use_id] = (client, event_obj, time.time())
                self.event_received.emit(data)
                event_obj.wait(timeout=86400)
                with self._lock:
                    if resolved_tool_use_id in self._pending:
                        try:
                            client.sendall(json.dumps({"decision": "deny", "reason": "timeout"}).encode("utf-8"))
                            client.close()
                        except OSError:
                            pass
                        self._pending.pop(resolved_tool_use_id, None)
                return
            else:
                # No tool_use_id available, cannot respond; close socket and emit as regular event
                client.close()
                self.event_received.emit(data)
                return

        # Non-permission events: close socket immediately
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
            # 轮poll检测到的 waiting 状态不生成 PermissionRequested（没有 tool_use_id，Allow 点不了）
            # 真正的 PermissionCard 只由 PermissionRequest hook 生成（带 tool_use_id）
            action = waiting_for
            if waiting_for.startswith("approve "):
                action = waiting_for[8:]
            event = ProgressUpdated(
                session_id=session_id,
                message=f"等待批准: {action}",
                payload={"status": "waiting", "waitingFor": waiting_for, "cwd": cwd},
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
        if not event_name:
            event_name = data.get("hook_event_name", "")
        session_id = data.get("session_id", data.get("sessionId", ""))
        payload = data.get("payload", {})
        timestamp = data.get("timestamp", time.time())

        for key in ("tool", "tool_input", "message", "status", "cwd", "pid", "tty"):
            if key in data:
                payload[key] = data[key]
        # Claude Code 使用驼峰命名 toolUseId，统一为下划线形式
        if "toolUseId" in data:
            payload["tool_use_id"] = data["toolUseId"]
        elif "tool_use_id" in data:
            payload["tool_use_id"] = data["tool_use_id"]

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
            # PreToolUse is only used for caching tool_use_id, do not create a card
            return None

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
