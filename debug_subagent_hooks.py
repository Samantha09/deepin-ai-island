#!/usr/bin/env python3
"""专门监听 socket 事件中的 SubagentStart/SubagentStop hook。"""

import json
import socket
import sys
import time
from datetime import datetime

SOCKET_PATH = "/tmp/ai-island.sock"
LOG_FILE = "/tmp/subagent_hooks.log"

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def main():
    log("=== Subagent Hook 监听启动 ===")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(SOCKET_PATH)
    except Exception as e:
        log(f"连接 socket 失败: {e}")
        return

    log("已连接到 socket，等待事件...")
    print("\n请在另一个终端触发子 Agent，观察这里是否有 SubagentStart/SubagentStop 事件输出。\n")

    buffer = b""
    try:
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buffer += chunk
            try:
                data = json.loads(buffer.decode("utf-8"))
                buffer = b""
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            event_name = data.get("event", data.get("hook_event_name", ""))
            session_id = data.get("session_id", data.get("sessionId", ""))

            # 只记录 subagent 相关事件和所有事件类型（用于发现未知事件）
            if "subagent" in event_name.lower() or "Subagent" in str(data):
                log(f"[SUBAGENT EVENT] {event_name} | session={session_id}")
                log(f"  RAW: {json.dumps(data, ensure_ascii=False)[:500]}")
            elif event_name in ("SessionStart", "SessionEnd"):
                log(f"[SESSION EVENT] {event_name} | session={session_id}")
                log(f"  RAW: {json.dumps(data, ensure_ascii=False)[:300]}")
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        log("=== 监听结束 ===")

if __name__ == "__main__":
    main()
