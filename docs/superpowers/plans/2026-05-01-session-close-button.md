# 会话列表关闭按钮与排序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI Island 会话卡片最右侧增加悬停时显示的关闭按钮，并按状态+最后更新时间排序会话列表。

**Architecture:** Session 模型新增 `last_updated` 时间戳并在事件到达时更新；前端通过 QWebChannel 通知 Python 关闭会话；列表推送时按状态分组后组内按时间降序。

**Tech Stack:** PySide6, Python 3.12+, HTML/JS/SVG

---

### Task 1: Session 模型增加 `last_updated` 字段（TDD）

**Files:**
- Create: `tests/test_session.py`
- Modify: `island_ui/session.py`

- [ ] **Step 1: 编写测试**

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from island_ui.session import Session
from island_ui.events import ChatMessage, ProgressUpdated


def test_session_last_updated_default():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    assert s.last_updated > 0
    assert s.last_updated >= s.start_time


def test_session_last_updated_on_add_event():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    before = s.last_updated
    time.sleep(0.01)
    s.add_event(ChatMessage(session_id="s1", role="user", content="hello"))
    assert s.last_updated > before


def test_session_last_updated_reflects_latest_event():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    s.add_event(ChatMessage(session_id="s1", role="user", content="first"))
    time.sleep(0.01)
    s.add_event(ProgressUpdated(session_id="s1", message="second"))
    assert s.last_updated == s.events[-1].timestamp


if __name__ == "__main__":
    test_session_last_updated_default()
    test_session_last_updated_on_add_event()
    test_session_last_updated_reflects_latest_event()
    print("All session tests passed!")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/san/PycharmProjects/deepin-ai-island && source .venv/bin/activate && python tests/test_session.py`
Expected: FAIL (AttributeError: 'Session' object has no attribute 'last_updated')

- [ ] **Step 3: 实现 `last_updated` 字段**

在 `island_ui/session.py` 中：
1. `last_updated: float = field(default_factory=lambda: datetime.now().timestamp())`
2. `add_event()` 末尾追加：`self.last_updated = event.timestamp`

```python
@dataclass
class Session:
    id: str
    name: str
    agent: str
    terminal: str
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "running"
    events: list[Event] = field(default_factory=list)
    resolved_tool_use_ids: set[str] = field(default_factory=set)

    # ... existing methods ...

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        self.last_updated = event.timestamp
        # ... rest of existing logic ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python tests/test_session.py`
Expected: All session tests passed!

- [ ] **Step 5: Commit**

```bash
git add tests/test_session.py island_ui/session.py
git commit -m "feat(session): 增加 last_updated 字段并在 add_event 时更新"
```

---

### Task 2: Python 后端增加关闭会话能力与排序

**Files:**
- Modify: `island_ui/island_window.py`

- [ ] **Step 1: 在 `IslandBridge` 中新增槽函数**

在 `IslandBridge` 类中，紧跟 `respondPermission` 之后添加：

```python
@Slot(str)
def closeSession(self, session_id: str) -> None:
    self.window.close_session(session_id)
```

- [ ] **Step 2: 在 `IslandWindow` 中新增 `close_session` 方法**

在 `IslandWindow` 类的 `respond_permission` 方法之后添加：

```python
def close_session(self, session_id: str) -> None:
    self._sessions.pop(session_id, None)
    self._push_sessions_to_web()
```

- [ ] **Step 3: 修改 `_push_sessions_to_web` 加入组内时间排序**

在构建完 `waiting_sessions`、`running_sessions`、`other_sessions` 之后、合并之前，对每组按 `last_updated` 降序排列：

```python
# 在 _push_sessions_to_web 方法中，原有分组逻辑之后：
waiting_sessions.sort(key=lambda s: s["last_updated"], reverse=True)
running_sessions.sort(key=lambda s: s["last_updated"], reverse=True)
other_sessions.sort(key=lambda s: s["last_updated"], reverse=True)
```

但注意：当前 `data` dict 中没有 `last_updated` 字段，需要在构建 data 时加入，前端不需要使用它，只是为了排序。或者更好的方式是在 Python 对象层面排序后再构建 dict。

建议改为：在遍历 `self._sessions.values()` 时保持现有逻辑，但在分组之后、构建 dict 之前排序：

```python
# 对每组按 last_updated 降序
for group in (waiting_sessions, running_sessions, other_sessions):
    group.sort(key=lambda s: s.last_updated, reverse=True)

# 然后构建 sessions_data（现有逻辑）
sessions_data = waiting_sessions + running_sessions + other_sessions
```

但这需要调整现有代码结构。现有代码是在循环内直接构建 dict 并分组。更简单的做法是：先分组收集 Session 对象，排序后再构建 dict。

重构后的关键部分：

```python
waiting_sessions = []
running_sessions = []
other_sessions = []
for session in self._sessions.values():
    if session.status == "needs_attention":
        waiting_sessions.append(session)
    elif session.status == "running":
        running_sessions.append(session)
    else:
        other_sessions.append(session)

# 按最后更新时间降序
for group in (waiting_sessions, running_sessions, other_sessions):
    group.sort(key=lambda s: s.last_updated, reverse=True)

sessions_data = []
for session in waiting_sessions + running_sessions + other_sessions:
    waiting_action = ""
    if session.status == "needs_attention":
        for event in reversed(session.events):
            if event.type == "permission.requested":
                tid = event.payload.get("tool_use_id", "")
                if not session.is_permission_resolved(tid):
                    waiting_action = event.payload.get("action", "")
                    break
    sessions_data.append({
        "id": session.id,
        "name": session.name,
        "agent": session.agent,
        "status": session.status,
        "waiting_action": waiting_action,
        "summary": self._build_session_summary(session),
    })
```

- [ ] **Step 4: Commit**

```bash
git add island_ui/island_window.py
git commit -m "feat(ui): 增加 close_session 接口与会话列表时间排序"
```

---

### Task 3: 前端增加关闭按钮 UI

**Files:**
- Modify: `island_ui/web/island.html`

- [ ] **Step 1: 增加关闭按钮 CSS**

在 `<style>` 中 `.session-card-row` 之后添加：

```css
/* 关闭按钮 */
.session-close-btn {
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0;
  transition: opacity 140ms ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: 8px;
}
.session-card:hover .session-close-btn {
  opacity: 1;
}
.session-close-btn svg {
  width: 100%;
  height: 100%;
  fill: rgba(255, 255, 255, 0.4);
  transition: fill 140ms ease;
}
.session-close-btn:hover svg {
  fill: #EF4444;
}
```

- [ ] **Step 2: 修改 JS 渲染逻辑加入关闭按钮**

在 `window.updateSessions` 中，创建 `row` 之后、追加到 `card` 之前，在 `row` 的最右侧插入关闭按钮：

```javascript
// 在 row.appendChild(left) 之后添加：

const closeBtn = document.createElement("button");
closeBtn.className = "session-close-btn";
closeBtn.type = "button";
closeBtn.innerHTML = '<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path d="M608 112a112 112 0 0 1 111.616 102.784l0.384 9.216v16h144a48 48 0 0 1 6.528 95.552l-6.528 0.448h-48v400a176 176 0 0 1-165.248 175.68L640 912H384a176 176 0 0 1-175.68-165.248L208 736V336H160a48 48 0 0 1-47.552-41.472L112 288a48 48 0 0 1 41.472-47.552L160 240h144V224a112 112 0 0 1 102.784-111.616L416 112h192z m112 224h-416v400c0 41.408 31.488 75.52 71.808 79.616L384 816h256a80 80 0 0 0 79.616-71.808l0.384-8.192V336zM416 432a48 48 0 0 1 47.552 41.472l0.448 6.528v192a48 48 0 0 1-95.552 6.528L368 672v-192a48 48 0 0 1 48-48z m192 0a48 48 0 0 1 48 48v192a48 48 0 1 1-96 0v-192a48 48 0 0 1 48-48z m0-224h-192a16 16 0 0 0-15.552 12.352L400 224v16h224V224a16 16 0 0 0-12.352-15.552L608 208z"/></svg>';
closeBtn.addEventListener("click", function (e) {
  e.stopPropagation();
  if (bridge) bridge.closeSession(session.id);
});
row.appendChild(closeBtn);
```

注意：这段代码要放在 `row.appendChild(left)` 之后、`card.appendChild(row)` 之前。

- [ ] **Step 3: Commit**

```bash
git add island_ui/web/island.html
git commit -m "feat(ui): 会话卡片增加悬停关闭按钮"
```

---

### Task 4: 集成验证

**Files:**
- None (runtime verification)

- [ ] **Step 1: Mock 模式启动验证 UI**

Run: `source .venv/bin/activate && python island_ui/main.py --source mock`

验证 checklist：
- [ ] 悬停展开面板，会话卡片右侧出现垃圾桶图标
- [ ] 鼠标移到图标上，颜色从灰色变红色
- [ ] 点击图标后，该会话从列表消失
- [ ] 多个会话时，needs_attention 组在前，同组内最后更新的在前

- [ ] **Step 2: Socket 事件注入测试（验证关闭后重现）**

在另一个终端运行 Python 脚本注入事件：

```python
import json, socket, time

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/tmp/ai-island.sock")

# 先关闭一个已知 session（假设 ID 为 test-001）
# 然后重新注入该 session 的事件
sock.sendall(json.dumps({
    "event": "SessionStarted",
    "session_id": "test-001",
    "payload": {"task": "Reappearing session", "agent": "test"}
}).encode())
time.sleep(0.1)
sock.sendall(json.dumps({
    "event": "ChatMessage",
    "session_id": "test-001",
    "payload": {"role": "assistant", "content": "I am back"}
}).encode())
sock.close()
```

验证：被关闭的会话重新出现在列表中。

- [ ] **Step 3: 最终提交（如所有验证通过）**

```bash
git status
git log --oneline -5
```

---

## Spec Coverage Check

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 关闭按钮位置在 session-card-row 最右侧 | Task 3 |
| 默认 opacity:0，卡片 hover 时 opacity:1 | Task 3 CSS |
| SVG 颜色默认灰色，hover 变红色 | Task 3 CSS |
| 点击 stopPropagation + bridge.closeSession | Task 3 JS |
| Python close_session 从 self._sessions pop | Task 2 |
| Session 新增 last_updated，add_event 更新 | Task 1 |
| 列表按状态分组 + 组内 last_updated 降序 | Task 2 |

## Placeholder Scan

无 TBD、TODO、placeholder。所有步骤包含完整代码和命令。

## Type Consistency

- `closeSession` 槽函数签名：`session_id: str`
- `close_session` 方法签名：`session_id: str`
- `last_updated` 类型：`float`
- 桥接对象方法名前后一致：`closeSession`
