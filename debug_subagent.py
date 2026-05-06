#!/usr/bin/env python3
"""监控 Claude Code 子 Agent 创建的调试脚本。

用法:
    python debug_subagent.py          # 启动实时监控
    python debug_subagent.py --analyze # 分析已有日志
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

WATCH_DIR = Path.home() / ".claude"
SESSIONS_DIR = WATCH_DIR / "sessions"
PROJECTS_DIR = WATCH_DIR / "projects"
LOG_FILE = Path("/tmp/subagent_watch.log")

def log(msg: str):
    """记录带时间戳的日志到控制台和文件。

    Args:
        msg: 要记录的日志消息。
    """
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_sessions_snapshot():
    """获取当前所有会话文件的内容摘要。

    Returns:
        dict: 以文件名为键、会话摘要信息为值的字典。
    """
    result = {}
    if not SESSIONS_DIR.exists():
        return result
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            result[f.name] = {
                "sessionId": data.get("sessionId"),
                "status": data.get("status"),
                "cwd": data.get("cwd"),
                "waitingFor": data.get("waitingFor"),
                "keys": list(data.keys()),
            }
        except Exception:
            pass
    return result

def get_claude_processes():
    """获取所有 claude 相关进程。

    Returns:
        list[str]: 包含 "claude" 关键词的进程信息行列表。
    """
    try:
        out = subprocess.check_output(["ps", "-ef"], text=True)
        lines = [l for l in out.splitlines() if "claude" in l.lower() and "grep" not in l.lower()]
        return lines
    except Exception:
        return []

def get_env_of_pid(pid: str):
    """读取进程环境变量。

    Args:
        pid: 进程 ID。

    Returns:
        list[str]: 包含 CLAUDE、PARENT 或 SESSION 关键词的环境变量列表。
    """
    try:
        env_path = f"/proc/{pid}/environ"
        if os.path.exists(env_path):
            data = open(env_path, "rb").read()
            envs = data.decode("utf-8", errors="ignore").split("\x00")
            return [e for e in envs if e and ("CLAUDE" in e.upper() or "PARENT" in e.upper() or "SESSION" in e.upper())]
    except Exception:
        pass
    return []

def watch_loop():
    """主监控循环。

    持续监控会话文件变化和 Claude 进程变化，直到用户按下 Ctrl+C。
    """
    log("=== 子 Agent 监控启动 ===")
    log(f"监控目录: {WATCH_DIR}")
    log(f"日志文件: {LOG_FILE}")

    old_sessions = get_sessions_snapshot()
    old_processes = set(get_claude_processes())

    log(f"初始会话数: {len(old_sessions)}")
    log(f"初始 Claude 进程数: {len(old_processes)}")

    print("\n请现在触发子 Agent 创建（例如让 Claude 执行复杂任务或调用工具）...")
    print("监控运行中，按 Ctrl+C 停止\n")

    try:
        while True:
            time.sleep(1)

            # 1. 检查新会话文件
            new_sessions = get_sessions_snapshot()
            new_ids = set(new_sessions.keys()) - set(old_sessions.keys())
            if new_ids:
                for sid in new_ids:
                    data = new_sessions[sid]
                    log(f"[NEW SESSION] {sid}: {json.dumps(data, ensure_ascii=False)}")

            modified_ids = []
            for sid in new_sessions:
                if sid in old_sessions:
                    old = old_sessions[sid]
                    new = new_sessions[sid]
                    if old != new:
                        modified_ids.append(sid)
                        # 找出变化字段
                        changes = {}
                        for k in set(list(old.keys()) + list(new.keys())):
                            if old.get(k) != new.get(k):
                                changes[k] = {"from": old.get(k), "to": new.get(k)}
                        log(f"[MODIFIED] {sid}: {json.dumps(changes, ensure_ascii=False)}")

            old_sessions = new_sessions

            # 2. 检查新进程
            current_processes = set(get_claude_processes())
            new_procs = current_processes - old_processes
            gone_procs = old_processes - current_processes
            if new_procs:
                for p in new_procs:
                    log(f"[NEW PROCESS] {p}")
                    # 尝试提取 PID 并读取环境变量
                    parts = p.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        envs = get_env_of_pid(pid)
                        if envs:
                            log(f"  ENV: {envs}")
            if gone_procs:
                for p in gone_procs:
                    log(f"[GONE PROCESS] {p}")
            old_processes = current_processes

    except KeyboardInterrupt:
        log("=== 监控结束 ===")
        print(f"\n日志已保存到: {LOG_FILE}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        # 分析模式：读取已有日志
        if LOG_FILE.exists():
            print(LOG_FILE.read_text())
        else:
            print("无日志文件")
    else:
        watch_loop()
