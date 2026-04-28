#!/usr/bin/env python3
"""安装/卸载 AI Island hook 到 Claude Code 的 settings.json。

Claude Code 从 ~/.claude/settings.json 读取 hooks 配置。
本脚本在该文件中注册 AI Island 的 hook，不覆盖用户已有配置。
"""

import json
import os
import shutil
import sys
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
HOOK_SCRIPT = Path(__file__).parent / "ai_island_hook.py"

# 支持的 hook 事件（PermissionRequest 带超时以支持双向响应）
HOOK_EVENTS = {
    "SessionStart": [{"hooks": [{"type": "command", "command": ""}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": ""}]}],
    "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": ""}]}],
    "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": ""}]}],
    "PermissionRequest": [{"matcher": "*", "hooks": [{"type": "command", "command": "", "timeout": 86400}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": ""}]}],
    "Stop": [{"hooks": [{"type": "command", "command": ""}]}],
}


def _detect_python() -> str:
    for py in ["python3", "python"]:
        if shutil.which(py):
            return py
    return "python3"


def _make_command() -> str:
    python = _detect_python()
    return f"{python} {HOOK_SCRIPT.resolve()}"


def _is_ai_island_hook(cmd: str) -> bool:
    return "ai_island_hook.py" in cmd


def _clean_existing_hooks(settings: dict) -> dict:
    """从 settings 中移除旧的 AI Island hook 条目。"""
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return settings

    cleaned = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            cleaned[event] = entries
            continue
        new_entries = []
        for entry in entries:
            if isinstance(entry, dict) and "hooks" in entry:
                inner = entry["hooks"]
                if isinstance(inner, list):
                    inner = [h for h in inner if isinstance(h, dict) and not _is_ai_island_hook(h.get("command", ""))]
                    if inner:
                        new_entry = dict(entry)
                        new_entry["hooks"] = inner
                        new_entries.append(new_entry)
                else:
                    new_entries.append(entry)
            else:
                new_entries.append(entry)
        if new_entries:
            cleaned[event] = new_entries

    if cleaned:
        settings["hooks"] = cleaned
    elif "hooks" in settings:
        del settings["hooks"]
    return settings


def install():
    hook_cmd = _make_command()

    settings = {}
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"警告: {SETTINGS_PATH} 解析失败，将重建", file=sys.stderr)
            settings = {}

    # 先清理旧配置
    settings = _clean_existing_hooks(settings)

    # 注册新配置
    hooks = settings.setdefault("hooks", {})
    for event, config_template in HOOK_EVENTS.items():
        entries = list(hooks.get(event, []))
        for cfg in config_template:
            new_cfg = json.loads(json.dumps(cfg))  # 深拷贝
            if "hooks" in new_cfg:
                for h in new_cfg["hooks"]:
                    h["command"] = hook_cmd
            entries.append(new_cfg)
        hooks[event] = entries

    # 写入文件
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[AI Island] Hook 已安装到 {SETTINGS_PATH}")
    print(f"[AI Island] 重启 Claude Code 后生效")


def uninstall():
    if not SETTINGS_PATH.exists():
        print("[AI Island] settings.json 不存在，无需卸载")
        return

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except json.JSONDecodeError:
        print("[AI Island] settings.json 损坏，无法卸载")
        return

    original = json.dumps(settings, sort_keys=True)
    settings = _clean_existing_hooks(settings)

    if json.dumps(settings, sort_keys=True) == original:
        print("[AI Island] 未找到已安装的 hook")
        return

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("[AI Island] Hook 已卸载")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--uninstall", "-u"):
        uninstall()
    else:
        install()
