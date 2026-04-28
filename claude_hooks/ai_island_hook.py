#!/usr/bin/env python3
"""Claude Code hook 脚本：通过 Unix Socket 与 AI Island 通信。

Claude Code 在触发 hook 时，将事件 JSON 写入本脚本的 stdin，
本脚本通过 Unix Socket 转发给 AI Island UI，并在 PermissionRequest 时等待响应。
"""

import json
import os
import socket
import sys
import time

# Unix Socket 路径，与 AI Island 服务端保持一致
SOCKET_PATH = "/tmp/ai-island.sock"
# PermissionRequest 最大等待时间（秒）
PERMISSION_TIMEOUT = 86400


def send_event_and_wait(data: dict) -> dict:
    """通过 Unix Socket 发送事件，PermissionRequest 时等待响应。"""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except (socket.error, OSError) as e:
        # 连接失败时静默放行，避免阻塞 Claude Code
        print(json.dumps({"systemMessage": f"AI Island 未运行: {e}"}), file=sys.stdout)
        return {}

    # 只有 PermissionRequest 需要等待响应
    if data.get("event") == "PermissionRequest":
        sock.settimeout(PERMISSION_TIMEOUT)
        try:
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                # 尝试解析完整 JSON
                try:
                    resp = json.loads(b"".join(chunks).decode("utf-8"))
                    return resp
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        except socket.timeout:
            # 超时默认拒绝
            return {"decision": "deny", "reason": "timeout"}
        except OSError:
            return {"decision": "deny", "reason": "connection lost"}
    else:
        # 其他事件不需要响应，直接关闭
        sock.close()
        return {}

    sock.close()
    return {}


def main():
    try:
        event_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # stdin 不是合法 JSON，静默退出
        sys.exit(0)

    # 补充事件类型标记（Claude Code hook stdin 里自带 event 字段）
    response = send_event_and_wait(event_data)

    # 如果有响应，输出给 Claude Code
    if response:
        print(json.dumps(response), file=sys.stdout)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
