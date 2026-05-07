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


def _infer_terminal_app() -> str:
    """通过进程树向上遍历，推断当前终端应用类型。"""
    import subprocess
    try:
        pid = os.getpid()
        for _ in range(16):
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True, text=True, timeout=1.0
            )
            if result.returncode != 0:
                break
            ppid = result.stdout.strip()
            if not ppid or ppid in ("0", "1"):
                break
            pid = int(ppid)
            comm_result = subprocess.run(
                ["ps", "-o", "comm=", "-p", str(pid)],
                capture_output=True, text=True, timeout=1.0
            )
            if comm_result.returncode != 0:
                continue
            comm = comm_result.stdout.strip().lower()
            if "pycharm" in comm:
                return "pycharm"
            # Java 进程可能是 PyCharm 或其他 JetBrains IDE
            if "java" in comm:
                cmdline_result = subprocess.run(
                    ["ps", "-o", "command=", "-p", str(pid)],
                    capture_output=True, text=True, timeout=1.0
                )
                if cmdline_result.returncode == 0:
                    cmdline = cmdline_result.stdout.strip().lower()
                    if "pycharm" in cmdline:
                        return "pycharm"
                    if "idea" in cmdline:
                        return "idea"
                    if "webstorm" in cmdline:
                        return "webstorm"
                    if "goland" in cmdline:
                        return "goland"
                    if "clion" in cmdline:
                        return "clion"
            if "deepin-terminal" in comm:
                return "deepin-terminal"
            if "gnome-terminal" in comm:
                return "gnome-terminal"
            if "konsole" in comm:
                return "konsole"
            if "terminator" in comm:
                return "terminator"
            if "xterm" in comm:
                return "xterm"
            if comm in ("code", "vscode"):
                return "vscode"
    except Exception:
        pass
    return ""


def _get_terminal_env() -> dict:
    """获取终端环境信息（tmux、窗口标题等），用于 AI Island 跳转终端。"""
    import subprocess
    env = {}
    # tmux 信息
    tmux = os.environ.get("TMUX", "")
    if tmux:
        # TMUX 环境变量格式: /tmp/tmux-1000/default,1234,0
        # socket 路径是逗号前的部分
        env["tmux_socket"] = tmux.split(",")[0]
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#S"],
                capture_output=True, text=True, timeout=1.0
            )
            if result.returncode == 0:
                env["tmux_session"] = result.stdout.strip()
        except Exception:
            pass
    # 终端窗口信息（用 TTY 和终端类型定位，不用 X11 窗口标题）
    window_id = os.environ.get("WINDOWID", "")
    if window_id and window_id != "0":
        env["window_id"] = window_id

    # 终端类型（TERM_PROGRAM 比 X11 类名更稳定）
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program:
        env["terminal_app"] = term_program
    else:
        # 通过进程树向上推断终端应用类型
        env["terminal_app"] = _infer_terminal_app()

    # 当前 TTY（精确定位终端实例）
    # 方法1: 通过 stdin 文件描述符（Claude Code hook 中 stdin 是管道，此方式通常失败）
    try:
        tty = os.ttyname(0)
        if tty:
            env["terminal_tty"] = tty
    except (OSError, AttributeError):
        pass

    # 方法2: 通过 tty 命令（stdout 仍可能是 TTY）
    if "terminal_tty" not in env:
        try:
            result = subprocess.run(
                ["tty"], capture_output=True, text=True, timeout=1.0
            )
            if result.returncode == 0:
                tty_out = result.stdout.strip()
                if tty_out and "not a tty" not in tty_out:
                    env["terminal_tty"] = tty_out
        except Exception:
            pass

    # 方法3: 通过父进程 TTY（最后手段）
    if "terminal_tty" not in env:
        try:
            ppid = os.getppid()
            result = subprocess.run(
                ["ps", "-p", str(ppid), "-o", "tty="],
                capture_output=True, text=True, timeout=1.0
            )
            if result.returncode == 0:
                tty = result.stdout.strip()
                if tty and tty not in ("?", "??"):
                    env["terminal_tty"] = f"/dev/{tty}" if not tty.startswith("/") else tty
        except Exception:
            pass

    return env


def send_event_and_wait(data: dict) -> dict:
    """通过 Unix Socket 发送事件，PermissionRequest 时等待响应。"""
    # 补充终端环境信息到 payload
    if "payload" in data and isinstance(data["payload"], dict):
        data["payload"].update(_get_terminal_env())
    elif "payload" not in data:
        data["payload"] = _get_terminal_env()
    else:
        data["payload"] = {**_get_terminal_env(), "original": data["payload"]}

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
