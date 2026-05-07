# 一键清除已完成会话 + 设置菜单改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在主面板增加"清除已完成"按钮，并将设置按钮改造为下拉菜单，集成音效开关、音量调节、关于、退出功能。

**Architecture:** 前端（island.html）增加清除按钮（🗑️）和设置下拉菜单，通过 QWebChannel 调用后端（island_window.py）新方法。后端操作 `_sessions` 和 `ConfigManager`。

**Tech Stack:** PySide6, QtWebChannel, HTML/CSS/JS, pytest

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `island_ui/island_window.py` | 修改 | IslandBridge / IslandWindow 增加清除和设置方法 |
| `island_ui/web/island.html` | 修改 | 增加清除按钮、设置下拉菜单 |
| `tests/test_clear_completed.py` | 新建 | 单元测试 |

---

## Task 1: 后端实现 — IslandWindow 增加清除和设置方法

**Files:**
- Modify: `island_ui/island_window.py`

- [ ] **Step 1: IslandBridge 增加新 Slot 方法**

在 `island_ui/island_window.py` 的 `IslandBridge` 类中，现有 Slot 方法之后添加：

```python
    @Slot()
    def clearCompletedSessions(self) -> None:
        self.window.clear_completed_sessions()

    @Slot(bool)
    def setSoundEnabled(self, enabled: bool) -> None:
        self.window.set_sound_enabled(enabled)

    @Slot(int)
    def setSoundVolume(self, volume: int) -> None:
        self.window.set_sound_volume(volume)

    @Slot()
    def quitApp(self) -> None:
        self.window.quit_app()
```

- [ ] **Step 2: IslandWindow 增加实现方法**

在 `island_ui/island_window.py` 的 `IslandWindow` 类中，现有方法之后添加：

```python
    def clear_completed_sessions(self) -> None:
        """移除所有 completed 或 idle 状态的会话。"""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.status in ("completed", "idle")
        ]
        for sid in to_remove:
            old_timer = self._completed_timers.pop(sid, None)
            if old_timer is not None:
                old_timer.stop()
            self._sessions.pop(sid, None)
        if to_remove:
            self._push_sessions_to_web()

    def set_sound_enabled(self, enabled: bool) -> None:
        """设置音效开关。"""
        if self._config_manager is not None:
            self._config_manager.set("sound.enabled", bool(enabled))

    def set_sound_volume(self, volume: int) -> None:
        """设置音效音量（0-100）。"""
        if self._config_manager is not None:
            self._config_manager.set("sound.volume", max(0, min(100, int(volume))))

    def quit_app(self) -> None:
        """退出应用。"""
        QApplication.instance().quit()
```

- [ ] **Step 3: Commit**

```bash
git add island_ui/island_window.py
git commit -m "feat(window): 增加 clear_completed_sessions、音效设置、退出接口"
```

---

## Task 2: 前端实现 — island.html 增加清除按钮和设置下拉菜单

**Files:**
- Modify: `island_ui/web/island.html`

- [ ] **Step 1: HTML 结构修改**

将 `island_ui/web/island.html` 中 `<div class="status-right">` 部分替换为：

```html
        <div class="status-right">
          <button id="clear-btn" type="button" aria-label="clear completed">🗑</button>
          <button id="settings-btn" type="button" aria-label="settings">⋯</button>
          <div id="settings-menu" class="hidden">
            <label class="menu-item">
              <span>音效</span>
              <input type="checkbox" id="sound-toggle" checked>
            </label>
            <label class="menu-item">
              <span>音量</span>
              <input type="range" id="sound-volume" min="0" max="100" value="50">
            </label>
            <div class="menu-divider"></div>
            <div class="menu-item" id="menu-about">关于</div>
            <div class="menu-item" id="menu-quit">退出</div>
          </div>
        </div>
```

- [ ] **Step 2: CSS 样式添加**

在 `<style>` 标签中，`.status-right` 样式之后添加：

```css
    #clear-btn {
      background: transparent;
      border: none;
      color: #9A9A9A;
      font-size: 13px;
      cursor: pointer;
      padding: 2px 4px;
      border-radius: 4px;
      margin-right: 2px;
      line-height: 1;
    }
    #clear-btn:hover {
      color: #EF4444;
      background: rgba(239, 68, 68, 0.1);
    }
    #settings-menu {
      position: absolute;
      top: 28px;
      right: 4px;
      background: #1E1E1E;
      border: 1px solid #333;
      border-radius: 8px;
      padding: 6px 0;
      min-width: 160px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      z-index: 100;
      opacity: 0;
      transform: scale(0.95);
      transition: opacity 0.15s ease, transform 0.15s ease;
      pointer-events: none;
    }
    #settings-menu.visible {
      opacity: 1;
      transform: scale(1);
      pointer-events: auto;
    }
    #settings-menu.hidden {
      display: none;
    }
    .menu-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 14px;
      color: #E5E5E5;
      font-size: 13px;
      cursor: pointer;
      transition: background 0.1s;
    }
    .menu-item:hover {
      background: #2A2A2A;
    }
    .menu-item input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: #66E8F8;
      cursor: pointer;
    }
    .menu-item input[type="range"] {
      width: 70px;
      cursor: pointer;
    }
    .menu-divider {
      height: 1px;
      background: #333;
      margin: 6px 10px;
    }
```

- [ ] **Step 3: JavaScript 交互逻辑**

在 `<script>` 标签中，现有 `settingsBtn` 事件监听器部分替换为：

```javascript
    const clearBtn = document.getElementById("clear-btn");
    const settingsMenu = document.getElementById("settings-menu");
    const soundToggle = document.getElementById("sound-toggle");
    const soundVolume = document.getElementById("sound-volume");
    const menuAbout = document.getElementById("menu-about");
    const menuQuit = document.getElementById("menu-quit");

    // 清除按钮点击
    clearBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (bridge) bridge.clearCompletedSessions();
    });

    // 设置按钮点击 —— 切换下拉菜单
    settingsBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (settingsMenu.classList.contains("visible")) {
        settingsMenu.classList.remove("visible");
        setTimeout(function () {
          if (!settingsMenu.classList.contains("visible")) {
            settingsMenu.classList.add("hidden");
          }
        }, 150);
      } else {
        settingsMenu.classList.remove("hidden");
        // 强制重排以确保过渡动画生效
        settingsMenu.offsetHeight;
        settingsMenu.classList.add("visible");
      }
    });

    // 音效开关
    soundToggle.addEventListener("change", function () {
      if (bridge) bridge.setSoundEnabled(soundToggle.checked);
    });

    // 音量滑块
    soundVolume.addEventListener("input", function () {
      if (bridge) bridge.setSoundVolume(parseInt(soundVolume.value, 10));
    });

    // 关于
    menuAbout.addEventListener("click", function (e) {
      e.stopPropagation();
      alert("AI Island v1.0.0");
      closeSettingsMenu();
    });

    // 退出
    menuQuit.addEventListener("click", function (e) {
      e.stopPropagation();
      if (bridge) bridge.quitApp();
    });

    function closeSettingsMenu() {
      settingsMenu.classList.remove("visible");
      setTimeout(function () {
        if (!settingsMenu.classList.contains("visible")) {
          settingsMenu.classList.add("hidden");
        }
      }, 150);
    }

    // 点击页面其他区域关闭菜单
    document.addEventListener("click", function () {
      if (settingsMenu.classList.contains("visible")) {
        closeSettingsMenu();
      }
    });

    // 阻止菜单内部点击冒泡
    settingsMenu.addEventListener("click", function (e) {
      e.stopPropagation();
    });
```

- [ ] **Step 4: Commit**

```bash
git add island_ui/web/island.html
git commit -m "feat(ui): 增加清除已完成按钮和设置下拉菜单"
```

---

## Task 3: 编写单元测试

**Files:**
- Create: `tests/test_clear_completed.py`

- [ ] **Step 1: 编写测试代码**

```python
# tests/test_clear_completed.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock

from island_ui.session import Session
from island_ui.events import SessionStarted, SessionEnded, ProgressUpdated


def _make_window():
    """构造一个带 sessions 的 mock window。"""
    window = MagicMock()
    window._sessions = {}
    window._completed_timers = {}
    window._config_manager = MagicMock()

    def _push():
        pass
    window._push_sessions_to_web = _push

    # 绑定要测试的方法
    from island_ui.island_window import IslandWindow
    window.clear_completed_sessions = lambda: IslandWindow.clear_completed_sessions(window)
    window.set_sound_enabled = lambda e: IslandWindow.set_sound_enabled(window, e)
    window.set_sound_volume = lambda v: IslandWindow.set_sound_volume(window, v)

    return window


def test_clear_completed_removes_completed_and_idle():
    window = _make_window()
    s1 = Session(id="s1", name="Running", agent="test", terminal="")
    s1.status = "running"
    s2 = Session(id="s2", name="Completed", agent="test", terminal="")
    s2.status = "completed"
    s3 = Session(id="s3", name="Idle", agent="test", terminal="")
    s3.status = "idle"
    s4 = Session(id="s4", name="Needs Attention", agent="test", terminal="")
    s4.status = "needs_attention"

    window._sessions = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    window.clear_completed_sessions()

    assert "s1" in window._sessions
    assert "s2" not in window._sessions
    assert "s3" not in window._sessions
    assert "s4" in window._sessions


def test_clear_completed_cleans_timers():
    window = _make_window()
    from PySide6.QtCore import QTimer
    timer = QTimer()
    window._completed_timers["s2"] = timer

    s = Session(id="s2", name="Completed", agent="test", terminal="")
    s.status = "completed"
    window._sessions = {"s2": s}
    window.clear_completed_sessions()

    assert "s2" not in window._completed_timers


def test_clear_completed_no_op_when_nothing_to_remove():
    window = _make_window()
    s1 = Session(id="s1", name="Running", agent="test", terminal="")
    s1.status = "running"
    window._sessions = {"s1": s1}

    window.clear_completed_sessions()
    assert "s1" in window._sessions


def test_set_sound_enabled_updates_config():
    window = _make_window()
    window.set_sound_enabled(False)
    window._config_manager.set.assert_called_once_with("sound.enabled", False)


def test_set_sound_volume_clamps_and_updates_config():
    window = _make_window()
    window.set_sound_volume(150)
    window._config_manager.set.assert_called_once_with("sound.volume", 100)

    window._config_manager.reset_mock()
    window.set_sound_volume(-10)
    window._config_manager.set.assert_called_once_with("sound.volume", 0)


if __name__ == "__main__":
    test_clear_completed_removes_completed_and_idle()
    test_clear_completed_cleans_timers()
    test_clear_completed_no_op_when_nothing_to_remove()
    test_set_sound_enabled_updates_config()
    test_set_sound_volume_clamps_and_updates_config()
    print("All clear-completed tests passed!")
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/san/PycharmProjects/deepin-ai-island
source .venv/bin/activate
pytest tests/test_clear_completed.py -v
```

Expected: 5 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_clear_completed.py
git commit -m "test: 增加 clear_completed_sessions 和音效设置单元测试"
```

---

## Task 4: Mock 模式集成验证

**Files:**
- 无新增/修改文件

- [ ] **Step 1: 启动 Mock 模式**

```bash
cd /home/san/PycharmProjects/deepin-ai-island
source .venv/bin/activate
python island_ui/main.py --source mock
```

- [ ] **Step 2: 验证清单**

- [ ] 主面板右上角出现 🗑 按钮和 ⋯ 按钮
- [ ] 点击 🗑，所有 completed/idle 会话被移除，running/needs_attention 保留
- [ ] 点击 ⋯ 弹出下拉菜单，包含"音效"开关、"音量"滑块、分隔线、"关于"、"退出"
- [ ] 点击菜单外部，菜单自动关闭
- [ ] 切换音效开关，观察配置变化（可通过日志或配置文件验证）
- [ ] 拖动音量滑块，观察配置变化
- [ ] 点击"关于"，弹出版本信息
- [ ] 点击"退出"，应用正常退出

- [ ] **Step 3: 提交（如有调整）**

```bash
# 如有修复，按需提交
```

---

## Self-Review

**Spec coverage:**
- ✅ 清除按钮 → Task 2 Step 1
- ✅ 清除范围（completed + idle）→ Task 1 Step 2
- ✅ 直接清除无确认 → Task 2 Step 1 中无 confirm
- ✅ 设置下拉菜单 → Task 2
- ✅ 音效开关 → Task 2 Step 1 + Step 3
- ✅ 音量滑块 → Task 2 Step 1 + Step 3
- ✅ 关于 → Task 2 Step 3
- ✅ 退出 → Task 2 Step 3
- ✅ 后端通信接口 → Task 1
- ✅ 单元测试 → Task 3
- ✅ Mock 验证 → Task 4

**Placeholder scan:** 无 TBD/TODO/"implement later"。

**Type consistency:** `clearCompletedSessions` / `setSoundEnabled` / `setSoundVolume` / `quitApp` 前后端名称一致。
