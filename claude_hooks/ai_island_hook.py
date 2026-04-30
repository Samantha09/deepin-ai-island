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
    except (socket.error, OSError):
        # AI Island 未运行时完全静默，不输出任何内容到 stdout
        # Claude Code 会回退到终端默认行为（自己弹权限提示）
        return {}

    # 只有 PermissionRequest 需要等待响应
    # Claude Code 使用 hook_event_name 而不是 event 字段
    event_name = data.get("event") or data.get("hook_event_name", "")
    if event_name == "PermissionRequest":
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

    # 调试日志：记录收到的所有 hook 事件
    try:
        with open("/tmp/ai-island-hook.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.time():.3f}] RECEIVED: {json.dumps(event_data, ensure_ascii=False)}\n")
    except Exception:
        pass

    # 补充事件类型标记（Claude Code hook stdin 里自带 event 字段）
    response = send_event_and_wait(event_data)

    # 调试日志：记录发送结果
    try:
        with open("/tmp/ai-island-hook.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.time():.3f}] RESPONSE: {json.dumps(response, ensure_ascii=False) if response else 'none'}\n")
    except Exception:
        pass

    # 如果有响应，包装成 Claude Code 需要的格式后输出
    if response:
        # Claude Code PermissionRequest hook 需要特定的响应格式
        # 参考: https://smartscope.blog/en/generative-ai/claude/claude-code-hooks-guide/
        # AI Island 返回 {"decision": "allow"} 或 {"decision": "deny", "reason": "..."}
        decision = response.get("decision", "")
        if not decision:
            # 兼容旧格式 {"approved": true}
            decision = "allow" if response.get("approved") else "deny"

        wrapped = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": decision
                }
            }
        }
        if decision == "deny":
            reason = response.get("reason", "")
            if reason:
                wrapped["hookSpecificOutput"]["decision"]["message"] = reason
            else:
                wrapped["hookSpecificOutput"]["decision"]["message"] = "Denied by user via AI Island"
        print(json.dumps(wrapped), file=sys.stdout)
        sys.stdout.flush()

    sys.exit(0)


if __name__ == "__main__":
    main()
