# macOS 平台支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在兼容现有 Linux 架构的基础上，新增 macOS 平台支持，使 AI Island 能在 macOS 上运行并支持终端跳转。

**Architecture:** 提取平台策略模式，新增 `island_ui/platform/` 包封装终端跳转差异（Linux 用 xdotool，macOS 用 AppleScript）。Hook 脚本和 Qt 平台配置按平台分支。Session 模型增加 `terminal_session_id` 字段支持 iTerm2/Ghostty 精确匹配。

**Tech Stack:** PySide6 (Qt6), Python 3.12+, AppleScript (osascript), Unix Socket

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `island_ui/platform/__init__.py` | Create | 工厂函数 `create_jumper()`，按平台返回对应 jumper |
| `island_ui/platform/base.py` | Create | `TerminalJumper` 抽象基类，定义 `jump()` 和 `is_available()` 接口 |
| `island_ui/platform/linux.py` | Create | `LinuxTerminalJumper`，xdotool 实现（从现有代码迁移） |
| `island_ui/platform/mac.py` | Create | `MacTerminalJumper`，AppleScript + `open -b` 实现 |
| `island_ui/session.py` | Modify | 增加 `terminal_session_id` 字段 |
| `island_ui/island_window.py` | Modify | `jump_to_terminal()` 改为调用 `self.jumper.jump()`；删除 xdotool 相关私有方法 |
| `island_ui/main.py` | Modify | `_fix_qt_platform()` 增加 macOS `cocoa` 分支 |
| `claude_hooks/ai_island_hook.py` | Modify | `_infer_terminal_app()` 增加 macOS 终端类型；`_get_terminal_env()` 增加 `terminal_session_id` 提取 |

---

### Task 1: Session 模型增加 terminal_session_id

**Files:**
- Modify: `island_ui/session.py:19-25`
- Modify: `island_ui/island_window.py`（`_update_session_terminal` 方法，需要 grep 定位）

- [ ] **Step 1: 增加字段**

在 `session.py` 的 `Session` dataclass 中，在 `terminal_app` 前增加 `terminal_session_id`：

```python
    # 终端跳转信息（由 hook 脚本提供）
    tmux_session: str = ""
    tmux_socket: str = ""
    window_id: str = ""
    window_title: str = ""
    terminal_tty: str = ""
    terminal_session_id: str = ""   # iTerm2/Ghostty session ID（macOS）
    terminal_app: str = ""
```

- [ ] **Step 2: 修改 `_update_session_terminal` 存储新字段**

找到 `island_ui/island_window.py` 中的 `_update_session_terminal` 方法（通常紧跟在 Session 创建附近），增加 `terminal_session_id` 的更新：

```python
    def _update_session_terminal(self, session: Session, payload: dict) -> None:
        """从 hook payload 中更新会话的终端环境信息。"""
        session.tmux_session = payload.get("tmux_session", "")
        session.tmux_socket = payload.get("tmux_socket", "")
        session.window_id = payload.get("window_id", "")
        session.window_title = payload.get("window_title", "")
        session.terminal_tty = payload.get("terminal_tty", "")
        session.terminal_app = payload.get("terminal_app", "")
        session.terminal_session_id = payload.get("terminal_session_id", "")
```

如果该方法不存在，说明当前代码直接在 `_on_event` 中赋值，需要找到对应位置统一改。

- [ ] **Step 3: 运行导入检查**

Run: `source .venv/bin/activate && python -c "from island_ui.session import Session; s = Session(id='x', name='x', agent='x', terminal='x'); print(s.terminal_session_id)"`
Expected: 空字符串输出，无异常

- [ ] **Step 4: Commit**

```bash
git add island_ui/session.py island_ui/island_window.py
git commit -m "feat(mac): Session 模型增加 terminal_session_id 字段"
```

---

### Task 2: Hook 脚本增加 macOS 终端检测

**Files:**
- Modify: `claude_hooks/ai_island_hook.py:20-77`
- Modify: `claude_hooks/ai_island_hook.py:80-149`

- [ ] **Step 1: 增加 macOS 终端推断**

在 `_infer_terminal_app()` 中，在现有终端判断之后、except 之前，增加 macOS 终端类型：

```python
            # macOS 终端
            if "iterm" in comm:
                return "iterm"
            if "ghostty" in comm:
                return "ghostty"
            if "warp" in comm:
                return "warp"
            if "wezterm" in comm:
                return "wezterm"
```

放在 `if comm in ("code", "vscode"):` 之后、`except Exception:` 之前。

- [ ] **Step 2: 增加 terminal_session_id 提取**

在 `_get_terminal_env()` 中，在 `env["terminal_app"] = ...` 之后，增加 `terminal_session_id` 提取：

```python
    # 终端 session ID（macOS iTerm2/Ghostty 用）
    iterm_session_id = os.environ.get("ITERM_SESSION_ID", "")
    if iterm_session_id:
        env["terminal_session_id"] = iterm_session_id
    ghostty_session_id = os.environ.get("GHOSTTY_SURFACE_ID", "")
    if ghostty_session_id:
        env["terminal_session_id"] = ghostty_session_id
```

- [ ] **Step 3: 验证 hook 脚本能正常导入**

Run: `python3 -c "import claude_hooks.ai_island_hook"`
Expected: 无异常

- [ ] **Step 4: Commit**

```bash
git add claude_hooks/ai_island_hook.py
git commit -m "feat(mac): hook 脚本增加 macOS 终端类型和 session ID 提取"
```

---

### Task 3: Qt 平台配置支持 macOS

**Files:**
- Modify: `island_ui/main.py:28-61`

- [ ] **Step 1: 重构 `_fix_qt_platform` 支持多平台**

将现有 `_fix_qt_platform` 替换为：

```python
import platform


def _fix_qt_platform() -> None:
    """配置 Qt 平台插件，兼容 Linux（xcb）和 macOS（cocoa）。"""
    system = platform.system()

    if system == "Darwin":
        os.environ["QT_QPA_PLATFORM"] = "cocoa"
        return

    if system == "Linux":
        # Deepin/DDE 桌面默认要求 dxcb 插件，但虚拟环境 PySide6 通常没有。
        # 强制使用标准 xcb 平台，并指向系统 Qt 插件路径。
        os.environ["QT_QPA_PLATFORM"] = "xcb"

        if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
            return

        # 检查虚拟环境是否自带平台插件
        try:
            import PySide6
            venv_plugins = Path(PySide6.__file__).parent / "plugins" / "platforms"
            if venv_plugins.exists() and any(venv_plugins.iterdir()):
                return
        except Exception:
            pass

        # 常见系统 Qt6 插件路径
        candidates = [
            "/usr/lib/x86_64-linux-gnu/qt6/plugins",
            "/usr/lib/x86_64-linux-gnu/qt5/plugins",
            "/usr/lib/qt6/plugins",
            "/usr/lib/qt5/plugins",
            "/usr/local/lib/qt6/plugins",
        ]
        for path in candidates:
            platforms = Path(path) / "platforms"
            if platforms.exists() and any(platforms.glob("libq*.so")):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = path
                break
```

- [ ] **Step 2: 运行导入检查**

Run: `source .venv/bin/activate && python -c "from island_ui.main import _fix_qt_platform; import platform; print(platform.system())"`
Expected: 输出 `Linux`，无异常

- [ ] **Step 3: Commit**

```bash
git add island_ui/main.py
git commit -m "feat(mac): Qt 平台配置支持 macOS cocoa"
```

---

### Task 4: 创建 TerminalJumper 抽象基类和工厂

**Files:**
- Create: `island_ui/platform/__init__.py`
- Create: `island_ui/platform/base.py`

- [ ] **Step 1: 创建 base.py**

```python
from abc import ABC, abstractmethod
from typing import Optional

from island_ui.session import Session


class TerminalJumper(ABC):
    """终端跳转抽象基类。Linux/macOS 分别实现具体跳转逻辑。"""

    @abstractmethod
    def jump(self, session: Session) -> bool:
        """尝试跳转到会话所在终端窗口/标签页。

        成功聚焦到目标终端返回 True，否则返回 False。
        """

    def is_available(self) -> bool:
        """当前平台是否具备跳转所需工具（如 xdotool、osascript）。"""
        return True

    def _log_jump(self, session_id: str, message: str) -> None:
        """记录跳转日志到 /tmp/ai-island-jump.log。"""
        try:
            with open("/tmp/ai-island-jump.log", "a", encoding="utf-8") as f:
                f.write(f"[{session_id}] {message}\n")
        except Exception:
            pass
```

- [ ] **Step 2: 创建 __init__.py**

```python
import platform

from island_ui.platform.base import TerminalJumper
from island_ui.platform.linux import LinuxTerminalJumper
from island_ui.platform.mac import MacTerminalJumper


def create_jumper() -> TerminalJumper:
    """按当前操作系统创建对应的 TerminalJumper 实例。"""
    system = platform.system()
    if system == "Darwin":
        return MacTerminalJumper()
    return LinuxTerminalJumper()
```

- [ ] **Step 3: 验证导入**

Run: `source .venv/bin/activate && python -c "from island_ui.platform import create_jumper; j = create_jumper(); print(type(j).__name__)"`
Expected: 输出 `LinuxTerminalJumper`（当前在 Linux 上运行），无异常

- [ ] **Step 4: Commit**

```bash
git add island_ui/platform/
git commit -m "feat(mac): 创建 TerminalJumper 抽象基类和平台工厂"
```

---

### Task 5: 创建 LinuxTerminalJumper

**Files:**
- Create: `island_ui/platform/linux.py`

- [ ] **Step 1: 实现 LinuxTerminalJumper**

将 `island_window.py` 中的 `jump_to_terminal`、`_activate_by_tty`、`_pick_best_window` 完整迁移到 `linux.py`，封装为 `LinuxTerminalJumper` 类：

```python
import os
import shutil
import subprocess
from typing import Optional

from island_ui.platform.base import TerminalJumper
from island_ui.session import Session


class LinuxTerminalJumper(TerminalJumper):
    """Linux 终端跳转：基于 xdotool 和进程树。"""

    def is_available(self) -> bool:
        return shutil.which("xdotool") is not None

    def jump(self, session: Session) -> bool:
        xdotool = shutil.which("xdotool")
        tmux_bin = shutil.which("tmux")
        session_id = session.id

        if not xdotool:
            self._log_jump(session_id, "xdotool not found")
            return False

        # 1. tmux: 找到活跃客户端的 TTY 或 pane TTY，然后激活对应窗口
        if session.tmux_session and tmux_bin:
            socket_args = []
            if session.tmux_socket:
                socket_args = ["-S", session.tmux_socket]

            try:
                result = subprocess.run(
                    [tmux_bin] + socket_args + ["list-clients", "-t", session.tmux_session, "-F", "#{client_tty}"],
                    capture_output=True, text=True, timeout=2.0
                )
                if result.returncode == 0:
                    for tty in result.stdout.strip().split("\n"):
                        tty = tty.strip()
                        if tty and self._activate_by_tty(tty, session, xdotool):
                            return True
            except Exception as e:
                self._log_jump(session_id, f"tmux client lookup exception: {e}")

            try:
                result = subprocess.run(
                    [tmux_bin] + socket_args + ["list-panes", "-t", session.tmux_session, "-F", "#{pane_tty}"],
                    capture_output=True, text=True, timeout=2.0
                )
                if result.returncode == 0:
                    for tty in result.stdout.strip().split("\n"):
                        tty = tty.strip()
                        if tty and self._activate_by_tty(tty, session, xdotool):
                            return True
            except Exception as e:
                self._log_jump(session_id, f"tmux pane lookup exception: {e}")

        # 2. 通过 TTY -> 进程树向上遍历 -> 找到有 X11 窗口的祖先进程
        if session.terminal_tty:
            if self._activate_by_tty(session.terminal_tty, session, xdotool):
                return True

        # 3. 通过 terminal_app 类名搜索窗口并激活
        if session.terminal_app:
            app_lower = session.terminal_app.lower()
            class_candidates = []
            if "pycharm" in app_lower:
                class_candidates = ["jetbrains-pycharm", "pycharm"]
            elif "vscode" in app_lower or "code" in app_lower:
                class_candidates = ["code", "vscode"]
            elif "deepin-terminal" in app_lower:
                class_candidates = ["deepin-terminal", "terminal"]
            elif "gnome-terminal" in app_lower:
                class_candidates = ["gnome-terminal", "terminal"]
            elif "konsole" in app_lower:
                class_candidates = ["konsole"]
            else:
                class_candidates = [app_lower]

            for cls in class_candidates:
                try:
                    r = subprocess.run(
                        [xdotool, "search", "--onlyvisible", "--class", cls],
                        capture_output=True, text=True, timeout=3.0
                    )
                    if r.returncode == 0:
                        wids = r.stdout.strip().split()
                        if wids:
                            best = self._pick_best_window(wids, session)
                            subprocess.run(
                                [xdotool, "windowactivate", best],
                                check=True, capture_output=True, timeout=3.0
                            )
                            self._log_jump(session_id, f"class search OK: class={cls}, window={best}")
                            return True
                except Exception as e:
                    self._log_jump(session_id, f"class search exception: {e}")

        # 4. 尝试通过窗口 ID 聚焦
        if session.window_id:
            try:
                subprocess.run(
                    [xdotool, "windowactivate", session.window_id],
                    check=True, capture_output=True, timeout=3.0
                )
                self._log_jump(session_id, f"windowactivate {session.window_id} OK")
                return True
            except Exception as e:
                self._log_jump(session_id, f"windowactivate FAIL: {e}")

        self._log_jump(session_id, "all methods exhausted")
        return False

    def _activate_by_tty(self, tty: str, session: Session, xdotool: str) -> bool:
        try:
            result = subprocess.run(
                ["ps", "-t", tty, "-o", "pid=", "--no-headers"],
                capture_output=True, text=True, timeout=3.0
            )
            if result.returncode != 0:
                return False
            pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            for pid in pids:
                current_pid = pid
                for _ in range(16):
                    ppid_result = subprocess.run(
                        ["ps", "-o", "ppid=", "-p", str(current_pid)],
                        capture_output=True, text=True, timeout=1.0
                    )
                    if ppid_result.returncode != 0:
                        break
                    ppid = ppid_result.stdout.strip()
                    if not ppid or ppid in ("0", "1"):
                        break
                    wid_result = subprocess.run(
                        [xdotool, "search", "--onlyvisible", "--pid", ppid],
                        capture_output=True, text=True, timeout=1.0
                    )
                    if wid_result.returncode == 0:
                        wids = wid_result.stdout.strip().split()
                        if wids:
                            best = self._pick_best_window(wids, session)
                            subprocess.run(
                                [xdotool, "windowactivate", best],
                                check=True, capture_output=True, timeout=3.0
                            )
                            self._log_jump(session.id, f"tty OK: tty={tty}, pid={ppid}, window={best}")
                            return True
                    current_pid = ppid
        except Exception:
            pass
        return False

    def _pick_best_window(self, wids: list[str], session: Session) -> str:
        if len(wids) <= 1:
            return wids[0] if wids else ""
        cwd = ""
        for event in reversed(session.events):
            cwd = event.payload.get("cwd", "")
            if cwd:
                break
        if not cwd:
            return wids[0]
        cwd_name = os.path.basename(cwd).lower()
        if not cwd_name:
            return wids[0]
        for wid in wids:
            try:
                result = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=1.0
                )
                if result.returncode == 0:
                    title = result.stdout.strip().lower()
                    if cwd_name in title:
                        return wid
            except Exception:
                pass
        return wids[0]
```

- [ ] **Step 2: 验证导入**

Run: `source .venv/bin/activate && python -c "from island_ui.platform.linux import LinuxTerminalJumper; j = LinuxTerminalJumper(); print('available:', j.is_available())"`
Expected: `available: True`（Linux 上有 xdotool），无异常

- [ ] **Step 3: Commit**

```bash
git add island_ui/platform/linux.py
git commit -m "feat(mac): 创建 LinuxTerminalJumper，迁移 xdotool 跳转逻辑"
```

---

### Task 6: 创建 MacTerminalJumper

**Files:**
- Create: `island_ui/platform/mac.py`

- [ ] **Step 1: 实现 MacTerminalJumper**

参考 open-vibe-island 的 `TerminalJumpService.swift` 和 `TerminalSessionAttachmentProbe.swift`：

```python
import os
import shutil
import subprocess

from island_ui.platform.base import TerminalJumper
from island_ui.session import Session


class MacTerminalJumper(TerminalJumper):
    """macOS 终端跳转：基于 AppleScript（osascript）。"""

    # bundle ID -> 应用别名列表
    KNOWN_APPS = {
        "iterm": ("com.googlecode.iterm2", ["iterm", "iterm2", "iterm.app"]),
        "ghostty": ("com.mitchellh.ghostty", ["ghostty"]),
        "terminal": ("com.apple.Terminal", ["terminal", "apple_terminal"]),
        "warp": ("dev.warp.Warp-Stable", ["warp", "warpterminal"]),
        "wezterm": ("com.github.wez.wezterm", ["wezterm"]),
        "vscode": ("com.microsoft.VSCode", ["vscode", "code", "visual studio code"]),
        "vscode-insiders": ("com.microsoft.VSCodeInsiders", ["vscode-insiders", "code-insiders"]),
        "cursor": ("com.todesktop.230313mzl4w4u92", ["cursor"]),
        "pycharm": ("com.jetbrains.pycharm", ["pycharm"]),
        "idea": ("com.jetbrains.intellij", ["idea", "intellij"]),
        "webstorm": ("com.jetbrains.WebStorm", ["webstorm"]),
        "goland": ("com.jetbrains.goland", ["goland"]),
        "clion": ("com.jetbrains.CLion", ["clion"]),
    }

    # VS Code 家族 CLI 命令映射
    VSCODE_CLI = {
        "com.microsoft.VSCode": "code",
        "com.microsoft.VSCodeInsiders": "code-insiders",
        "com.todesktop.230313mzl4w4u92": "cursor",
    }

    # JetBrains CLI 命令映射
    JETBRAINS_CLI = {
        "com.jetbrains.intellij": "idea",
        "com.jetbrains.WebStorm": "webstorm",
        "com.jetbrains.pycharm": "pycharm",
        "com.jetbrains.goland": "goland",
        "com.jetbrains.CLion": "clion",
    }

    def is_available(self) -> bool:
        return shutil.which("osascript") is not None

    def jump(self, session: Session) -> bool:
        session_id = session.id
        target = session.terminal_app.lower() if session.terminal_app else ""

        # 1. iTerm2: AppleScript 精确匹配 session ID 或 TTY
        if "iterm" in target:
            if self._jump_to_iterm(session):
                return True

        # 2. Terminal.app: AppleScript 匹配 TTY
        if target in ("terminal", "apple_terminal"):
            if self._jump_to_terminal_app(session):
                return True

        # 3. Ghostty: AppleScript 匹配 session ID
        if "ghostty" in target:
            if self._jump_to_ghostty(session):
                return True

        # 4. VS Code 家族: 使用 CLI 打开工作区
        for bundle_id, cli in self.VSCODE_CLI.items():
            aliases = [a for bid, (_, aliases) in self.KNOWN_APPS.items() if bid in ("vscode", "vscode-insiders", "cursor") for a in aliases]
            if any(a in target for a in aliases):
                if self._jump_to_vscode_family(session, cli):
                    return True
                break

        # 5. JetBrains: 使用 CLI 打开项目
        for bundle_id, cli in self.JETBRAINS_CLI.items():
            aliases = [a for bid, (_, aliases) in self.KNOWN_APPS.items() if bid in ("pycharm", "idea", "webstorm", "goland", "clion") for a in aliases]
            if any(a in target for a in aliases):
                if self._jump_to_jetbrains(session, cli):
                    return True
                break

        # 6. 兜底: open -b <bundle_id> 激活应用
        for app_key, (bundle_id, aliases) in self.KNOWN_APPS.items():
            if any(a in target for a in aliases):
                try:
                    subprocess.run(["open", "-b", bundle_id], check=True, timeout=5.0)
                    self._log_jump(session_id, f"Activated {app_key} via open -b")
                    return True
                except Exception as e:
                    self._log_jump(session_id, f"open -b fallback failed: {e}")
                break

        self._log_jump(session_id, "all macOS methods exhausted")
        return False

    def _run_applescript(self, script: str) -> str:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5.0
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

    def _jump_to_iterm(self, session: Session) -> bool:
        sid = session.terminal_session_id or ""
        tty = session.terminal_tty or ""
        script = f'''
        tell application "iTerm"
            if not (it is running) then return ""
            activate
            repeat with aWindow in windows
                repeat with aTab in tabs of aWindow
                    repeat with aSession in sessions of aTab
                        set matched to false
                        if "{sid}" is not "" and (id of aSession as text) is "{sid}" then
                            set matched to true
                        end if
                        if not matched and "{tty}" is not "" and (tty of aSession as text) is "{tty}" then
                            set matched to true
                        end if
                        if matched then
                            select aWindow
                            tell aWindow to select aTab
                            select aSession
                            return "matched"
                        end if
                    end repeat
                end repeat
            end repeat
        end tell
        return ""
        '''
        try:
            return self._run_applescript(script) == "matched"
        except Exception as e:
            self._log_jump(session.id, f"iTerm jump failed: {e}")
            return False

    def _jump_to_terminal_app(self, session: Session) -> bool:
        tty = session.terminal_tty or ""
        script = f'''
        tell application "Terminal"
            if not (it is running) then return ""
            activate
            repeat with aWindow in windows
                repeat with aTab in tabs of aWindow
                    if "{tty}" is not "" and (tty of aTab as text) is "{tty}" then
                        set selected of aTab to true
                        set frontmost of aWindow to true
                        return "matched"
                    end if
                end repeat
            end repeat
        end tell
        return ""
        '''
        try:
            return self._run_applescript(script) == "matched"
        except Exception as e:
            self._log_jump(session.id, f"Terminal.app jump failed: {e}")
            return False

    def _jump_to_ghostty(self, session: Session) -> bool:
        sid = session.terminal_session_id or ""
        script = f'''
        tell application "Ghostty"
            if not (it is running) then return ""
            activate
            repeat with aTerminal in terminals
                if "{sid}" is not "" and (id of aTerminal as text) is "{sid}" then
                    return "matched"
                end if
            end repeat
        end tell
        return ""
        '''
        try:
            return self._run_applescript(script) == "matched"
        except Exception as e:
            self._log_jump(session.id, f"Ghostty jump failed: {e}")
            return False

    def _jump_to_vscode_family(self, session: Session, cli: str) -> bool:
        cwd = ""
        for event in reversed(session.events):
            cwd = event.payload.get("cwd", "")
            if cwd:
                break
        if not cwd:
            return False
        try:
            subprocess.run([cli, "-r", cwd], check=True, timeout=5.0)
            self._log_jump(session.id, f"VSCode family jump OK: {cli} -r {cwd}")
            return True
        except Exception as e:
            self._log_jump(session.id, f"VSCode family jump failed: {e}")
            return False

    def _jump_to_jetbrains(self, session: Session, cli: str) -> bool:
        cwd = ""
        for event in reversed(session.events):
            cwd = event.payload.get("cwd", "")
            if cwd:
                break
        if not cwd:
            return False
        try:
            subprocess.run([cli, cwd], check=True, timeout=5.0)
            self._log_jump(session.id, f"JetBrains jump OK: {cli} {cwd}")
            return True
        except Exception as e:
            self._log_jump(session.id, f"JetBrains jump failed: {e}")
            return False
```

- [ ] **Step 2: 验证导入**

Run: `source .venv/bin/activate && python -c "from island_ui.platform.mac import MacTerminalJumper; j = MacTerminalJumper(); print('available:', j.is_available())"`
Expected: `available: False`（Linux 上无 osascript），无异常

- [ ] **Step 3: Commit**

```bash
git add island_ui/platform/mac.py
git commit -m "feat(mac): 创建 MacTerminalJumper，AppleScript 实现终端跳转"
```

---

### Task 7: 集成平台 jumper 到 IslandWindow

**Files:**
- Modify: `island_ui/island_window.py:462-574`（jump_to_terminal 及辅助方法）

- [ ] **Step 1: 修改 IslandWindow.__init__ 初始化 jumper**

在 `IslandWindow.__init__` 中（约第 240 行之后），添加：

```python
from island_ui.platform import create_jumper
self._jumper = create_jumper()
```

- [ ] **Step 2: 替换 jump_to_terminal 方法**

将原有的 `jump_to_terminal`、`_activate_by_tty`、`_pick_best_window` 三个方法替换为：

```python
    def jump_to_terminal(self, session_id: str) -> None:
        """跳转到会话所在的终端。平台实现由 TerminalJumper 子类提供。"""
        session = self._sessions.get(session_id)
        if not session:
            self._jumper._log_jump(session_id, "session not found")
            return
        self._jumper.jump(session)
```

- [ ] **Step 3: 删除已迁移的私有方法**

确认 `_activate_by_tty`、`_pick_best_window`、`_log_jump` 已从 `IslandWindow` 中删除（它们已迁移到 `LinuxTerminalJumper`）。

注意：`IslandWindow` 中如果还有其他地方调用 `_log_jump`，需要改为调用 `self._jumper._log_jump()`。

- [ ] **Step 4: 验证导入和现有行为**

Run: `source .venv/bin/activate && python -c "from island_ui.island_window import IslandWindow; print('OK')"`
Expected: 无异常

Run Mock 模式快速验证 UI 是否启动正常：
```bash
source .venv/bin/activate && timeout 5 python island_ui/main.py --source mock || true
```
Expected: Island 窗口正常出现，无崩溃

- [ ] **Step 5: Commit**

```bash
git add island_ui/island_window.py
git commit -m "feat(mac): IslandWindow 集成 TerminalJumper，删除已迁移的 xdotool 私有方法"
```

---

### Task 8: 端到端验证

**Files:**
- N/A（验证步骤）

- [ ] **Step 1: Linux 端验证终端跳转未回退**

启动 AI Island，在另一个终端注入事件并测试跳转：

```bash
# 终端 1：启动 AI Island
source .venv/bin/activate
python island_ui/main.py

# 终端 2：注入一个带终端信息的会话事件
python3 -c "
import json, socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/tmp/ai-island.sock')
sock.sendall(json.dumps({
    'event': 'SessionStart',
    'session_id': 'test-jump-001',
    'payload': {
        'agent': 'Claude Code',
        'task': 'test',
        'terminal': '/home/san',
        'terminal_tty': '/dev/pts/0',
        'terminal_app': 'deepin-terminal'
    }
}).encode())
sock.close()
"
```

然后点击会话卡片，观察 `/tmp/ai-island-jump.log` 是否有成功记录。

- [ ] **Step 2: 检查代码无残留 xdotool 调用在 IslandWindow 中**

Run: `grep -n "xdotool" island_ui/island_window.py`
Expected: 无输出（所有 xdotool 逻辑已迁移到 `linux.py`）

- [ ] **Step 3: 检查平台包结构完整**

Run: `ls -la island_ui/platform/`
Expected: 看到 `__init__.py`, `base.py`, `linux.py`, `mac.py`

- [ ] **Step 4: Commit 最终版本**

```bash
git add .
git status
git commit -m "feat(mac): 完整 macOS 平台支持（终端跳转、Qt 平台、Hook 脚本）"
```

---

## Spec Self-Review

**1. Spec coverage:**
- Session 模型扩展 -> Task 1
- Hook 脚本 macOS 终端检测 -> Task 2
- Qt 平台 cocoa 支持 -> Task 3
- TerminalJumper 抽象基类 -> Task 4
- Linux xdotool 迁移 -> Task 5
- macOS AppleScript 实现 -> Task 6
- IslandWindow 集成 -> Task 7
- 端到端验证 -> Task 8

**2. Placeholder scan:**
- 无 "TBD"、"TODO"、"implement later"
- 每个步骤都有完整代码
- 每个步骤都有验证命令

**3. Type consistency:**
- `Session.terminal_session_id: str = ""` 在 Task 1 定义，Task 2（hook）、Task 6（Mac jumper）中使用
- `TerminalJumper.jump(session: Session) -> bool` 在 Task 4 定义，Task 5/6/7 中实现/调用
- `create_jumper()` 在 Task 4 定义，Task 7 中调用

无类型不一致问题。
