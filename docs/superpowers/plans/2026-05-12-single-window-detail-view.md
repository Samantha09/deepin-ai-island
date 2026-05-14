# 主岛单窗口详情视图重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ExpandedWindow 详情视图合并到主岛 IslandWindow 中，实现单窗口内原地切换会话列表和详情视图。

**Architecture:** 删除 ExpandedWindow 独立窗口，将 expanded.html 的 CSS/JS 迁移到 island.html 的 `#detail-view` 容器中。Python 端保留 `update_session_detail` 数据推送方法，但改为向主岛的 web view 推送，由 JS 控制视图切换。

**Tech Stack:** PySide6, QWebEngineView, HTML/CSS/JS, Unix Socket

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `island_ui/web/island.html` | 新增 `#detail-view` 容器 + 详情样式 + 详情 JS |
| `island_ui/web/expanded.html` | 删除 |
| `island_ui/island_window.py` | 删除 ExpandedWindow/ExpandedBridge，修改 IslandBridge 和 IslandWindow |

---

## Task 1: island.html — 新增详情视图容器与样式

**Files:**
- Modify: `island_ui/web/island.html`

**Context:** 在现有 `#capsule` 内新增 `#detail-view`，与现有内容并列，默认隐藏。从 `expanded.html` 迁移所有详情相关 CSS。

- [ ] **Step 1: 在 `#capsule` 内新增 `#detail-view` 容器**

在 `#main-page` 同级位置（仍在 `#capsule` 内部）添加：

```html
<div id="detail-view">
  <button id="detail-back-btn" type="button" aria-label="返回">← 返回</button>
  <div id="detail-header">
    <div id="detail-title">会话详情</div>
    <div id="detail-agent"></div>
  </div>
  <div id="detail-content">
    <div class="empty-detail">暂无聊天记录</div>
  </div>
</div>
```

- [ ] **Step 2: 新增详情视图 CSS**

在现有样式之后插入：

```css
#detail-view {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  display: none;
  opacity: 0;
  flex-direction: column;
  padding: 12px;
  box-sizing: border-box;
  transition: opacity 180ms ease-out;
  overflow: hidden;
}
#detail-view.active {
  display: flex;
  opacity: 1;
}
#detail-back-btn {
  position: absolute;
  top: 8px; left: 10px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  z-index: 10;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 140ms ease;
}
#detail-back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
#detail-header {
  padding: 8px 0 6px 28px;
  flex-shrink: 0;
}
#detail-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#detail-agent {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}
#detail-content {
  flex: 1;
  overflow-y: auto;
  box-sizing: border-box;
}
#detail-content::-webkit-scrollbar { width: 0; background: transparent; }
```

- [ ] **Step 3: 从 expanded.html 迁移详情卡片样式**

将以下样式块从 `expanded.html` 迁移到 `island.html` 的 `<style>` 中：
- `.message-row` / `.message-bubble`
- `.permission-card` / `.permission-title` / `.permission-action` / `.permission-buttons` / `.perm-btn`
- `.question-card` / `.question-title` / `.question-options` / `.question-option-btn` / `.question-input-area` / `.question-input` / `.question-send-btn` / `.question-answer-result`
- `.empty-detail`
- `.message-bubble` 内的 Markdown 样式（`p`, `code`, `pre`, `blockquote`, `ul`, `ol`, `a`, `hr`, `strong`）

- [ ] **Step 4: Commit**

```bash
git add island_ui/web/island.html
git commit -m "feat(ui): island.html 新增详情视图容器与样式"
```

---

## Task 2: island.html — 迁移详情视图 JS

**Files:**
- Modify: `island_ui/web/island.html`

**Context:** 从 `expanded.html` 迁移所有详情渲染 JS，并新增 `showDetail`/`hideDetail` 视图切换函数。

- [ ] **Step 1: 获取 DOM 引用**

在现有 `const capsule = ...` 之后添加：

```javascript
const detailView = document.getElementById("detail-view");
const detailBackBtn = document.getElementById("detail-back-btn");
const detailTitle = document.getElementById("detail-title");
const detailAgent = document.getElementById("detail-agent");
const detailContent = document.getElementById("detail-content");
```

- [ ] **Step 2: 迁移 Markdown 渲染函数**

如果 `island.html` 中已有 `markdownToHtml` 等函数，则复用；如果没有，从 `expanded.html` 迁移完整的 `escapeHtml` / `processInline` / `markdownToHtml` 函数。

- [ ] **Step 3: 新增 showDetail / hideDetail**

```javascript
let currentDetailSessionId = null;
let resolvedPermissionsDetail = new Set();

window.showDetail = function (sessionId) {
  currentDetailSessionId = sessionId;
  detailView.classList.add("active");
};

window.hideDetail = function () {
  detailView.classList.remove("active");
  currentDetailSessionId = null;
  resolvedPermissionsDetail.clear();
};

detailBackBtn.addEventListener("click", function () {
  window.hideDetail();
});
```

- [ ] **Step 4: 迁移 updateSessionDetail 和相关渲染函数**

从 `expanded.html` 迁移 `updateSessionDetail`、`renderEvent`、`addMessage`、`addPermissionCard`、`respond`、`addQuestionCard`、`respondQuestion` 函数到 `island.html` 的 `<script>` 中。修改 `content` 变量引用为 `detailContent`，`currentSessionId` 改为 `currentDetailSessionId`，`resolvedPermissions` 改为 `resolvedPermissionsDetail`。

- [ ] **Step 5: Commit**

```bash
git add island_ui/web/island.html
git commit -m "feat(ui): island.html 迁移详情视图 JS 逻辑"
```

---

## Task 3: IslandBridge — 修改 Slot

**Files:**
- Modify: `island_ui/island_window.py:22-83` (IslandBridge)

**Context:** `selectSession` 不再打开 ExpandedWindow，改为推送详情数据并触发 JS 视图切换。新增 `showSessionDetail` Slot（复用现有 `selectSession` 逻辑）。删除 `openExpandedWindow` Slot。

- [ ] **Step 1: 修改 selectSession Slot**

将 `selectSession` 改为直接调用 `window.showSessionDetail`（即现有的 `select_session` 逻辑）：

```python
@Slot(str)
def selectSession(self, session_id: str) -> None:
    self.window.select_session(session_id)
```

保持不变（Python 端方法名仍为 `select_session`）。

- [ ] **Step 2: 删除 openExpandedWindow Slot**

删除 `openExpandedWindow` Slot（约 line 58-59）：

```python
@Slot()
def openExpandedWindow(self) -> None:
    self.window.open_expanded_window()
```

- [ ] **Step 3: Commit**

```bash
git add island_ui/island_window.py
git commit -m "refactor(bridge): 删除 openExpandedWindow Slot"
```

---

## Task 4: island_window.py — 修改 Python 端方法

**Files:**
- Modify: `island_ui/island_window.py`

**Context:** 修改 `select_session`、`respond_permission`、`respond_permission_all`、`respond_question` 等方法，不再操作 ExpandedWindow，改为直接推送数据或通知 JS 切换视图。

- [ ] **Step 1: 修改 select_session**

```python
def select_session(self, session_id: str) -> None:
    session = self._sessions.get(session_id)
    if not session:
        return
    self._permission_auto_close_timer.stop()
    self._push_session_detail(session)
    self.web_view.page().runJavaScript(
        "if (typeof window.showDetail === 'function') window.showDetail('" + session_id + "');"
    )
```

- [ ] **Step 2: 修改 respond_permission**

删除 `if self.expanded_window.isVisible(): self.expanded_window.close_to_main()` 块（约 line 1041-1042）。改为：

```python
# 审批完成后缩回详情视图
self.web_view.page().runJavaScript(
    "if (typeof window.hideDetail === 'function') window.hideDetail();"
)
```

- [ ] **Step 3: 修改 respond_permission_all**

同样删除 ExpandedWindow 相关代码，改为 `window.hideDetail()`。

- [ ] **Step 4: 修改 respond_question**

同样删除 ExpandedWindow 相关代码，改为 `window.hideDetail()`。

- [ ] **Step 5: Commit**

```bash
git add island_ui/island_window.py
git commit -m "refactor(window): 移除 ExpandedWindow 引用，改为 JS 视图切换"
```

---

## Task 5: island_window.py — 删除 ExpandedWindow 和 ExpandedBridge

**Files:**
- Modify: `island_ui/island_window.py`

**Context:** 删除 `ExpandedWindow` 类（约 line 114-234）、`ExpandedBridge` 类（约 line 86-112），以及所有引用它们的代码。

- [ ] **Step 1: 删除 ExpandedBridge 类**

删除 `ExpandedBridge` 类定义（line 86-112）。

- [ ] **Step 2: 删除 ExpandedWindow 类**

删除 `ExpandedWindow` 类定义（line 114-234）。

- [ ] **Step 3: 删除 IslandWindow 中的 expanded_window 引用**

删除：
- `self.expanded_window = ExpandedWindow(self)`（line 330）
- `open_expanded_window()` 方法（line 1119-1129）
- `on_expanded_closed()` 方法（line 1131-1144）
- `_toggle_visibility` 中的 `self.expanded_window.hide()`（line 1263）
- `_expanded_open` 标志及其所有引用

- [ ] **Step 4: Commit**

```bash
git add island_ui/island_window.py
git commit -m "refactor(window): 删除 ExpandedWindow 和 ExpandedBridge 类"
```

---

## Task 6: 删除 expanded.html

**Files:**
- Delete: `island_ui/web/expanded.html`

- [ ] **Step 1: 删除文件**

```bash
rm island_ui/web/expanded.html
git add -A
git commit -m "refactor(ui): 删除 expanded.html（功能已合并到 island.html）"
```

---

## Task 7: 回归测试

**Files:** 不涉及文件修改，纯验证

- [ ] **Step 1: Mock 模式验证视图切换**

```bash
source .venv/bin/activate
python island_ui/main.py --source mock
```

验证 checklist：
- [ ] 悬停展开后能看到会话列表
- [ ] 点击 s2-codex（含 QuestionAsked 的会话）进入详情视图
- [ ] 详情视图显示蓝色 Question Card 和选项按钮
- [ ] 点击返回按钮回到会话列表
- [ ] 无 JS 报错

- [ ] **Step 2: 运行测试套件**

```bash
source .venv/bin/activate
python -m pytest tests/test_ask_user_question.py tests/test_session.py tests/test_events.py -v
```

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "test: 单窗口视图切换回归测试通过"
```

---

## Self-Review Checklist

| Spec 要求 | 实现任务 |
|-----------|----------|
| 单窗口视图切换 | Task 1 + Task 2 (island.html 详情容器) |
| 返回按钮 | Task 1 (CSS + HTML) |
| 原地切换动画 | Task 1 (CSS opacity transition) |
| 删除 ExpandedWindow | Task 5 |
| 删除 expanded.html | Task 6 |
| 保留所有交互功能 | Task 2 (JS 迁移) + Task 4 (Python 修改) |
| 权限/提问响应后返回列表 | Task 4 (hideDetail JS 调用) |

**Placeholder scan:** 无 TBD/TODO，所有代码块完整。
**Type consistency:**
- `showDetail(sessionId)` / `hideDetail()` 在 Task 2 JS 和 Task 4 Python 中命名一致
- `updateSessionDetail(data)` 函数签名保持不变
