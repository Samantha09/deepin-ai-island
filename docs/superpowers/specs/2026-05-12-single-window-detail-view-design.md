# 主岛单窗口详情视图重构

## 背景

当前主岛（IslandWindow）和详情窗口（ExpandedWindow）是两个独立的 QWidget，各自加载不同的 HTML。点击会话卡片时打开 ExpandedWindow，主岛缩回胶囊，视觉上两个窗口尺寸不一致，切换生硬。

## 目标

将 ExpandedWindow 的详情视图合并到主岛内，实现单窗口视图切换：
- 会话列表和详情共享同一个 QWebEngineView
- 原地淡入淡出切换，无新窗口弹出
- 删除 ExpandedWindow 类和 expanded.html

## 设计

### 视图结构

在 `island.html` 中新增 `#detail-view` 容器，与 `#list-view` 并列，通过 CSS `opacity` + `transform` 切换：

```
island.html
├── #panel
│   ├── #list-view        ← 会话列表（现有内容）
│   │   ├── center-info（计数信息）
│   │   ├── #session-list（卡片容器）
│   │   └── #settings-menu
│   └── #detail-view      ← 新增：详情视图
│       ├── #detail-back-btn（返回按钮，左上角）
│       ├── #detail-header
│       │   ├── #detail-title
│       │   └── #detail-agent
│       └── #detail-content（消息气泡、权限卡片、提问卡片）
```

### 切换流程

1. **列表 → 详情**：
   - 点击会话卡片 → `bridge.showSessionDetail(id)`
   - Python 端 `_push_session_detail(session)` 推送详情数据到 JS
   - JS 调用 `window.showDetail(data)` → 隐藏 `#list-view`，显示 `#detail-view`，渲染内容

2. **详情 → 列表**：
   - 点击返回按钮 → JS 调用 `hideDetail()` → 反向切换
   - 无需 Python 参与，纯 JS 操作

3. **窗口尺寸**：
   - 详情视图复用主岛当前展开尺寸（`large_size` 460×320）
   - 不改变窗口大小，仅切换内容

### 数据流

```
用户点击卡片 → bridge.showSessionDetail(id)
  → Python: _push_session_detail(session)
  → JS: window.updateSessionDetail(data)  // 推送详情数据
  → JS: window.showDetail()               // 切换视图

用户点击返回 → JS: hideDetail()            // 纯前端操作

用户操作权限/提问 → bridge.respondPermission/respondQuestion  // 复用现有 IslandBridge
```

### Bridge 变更

**IslandBridge 新增：**
- `showSessionDetail(session_id)` → 推送详情数据并切换视图

**IslandBridge 修改：**
- `selectSession(session_id)` → 不再打开 ExpandedWindow，改为调用 `showSessionDetail`

**删除：**
- `ExpandedBridge` 类（整个删除）
- `openExpandedWindow` Slot

### Python 端变更

**新增：**
- `_push_session_detail(session)` → 构造详情数据，调用 JS `updateSessionDetail(data)` + `showDetail()`

**修改：**
- `select_session(session_id)` → 调用 `_push_session_detail` 而非 `open_expanded_window`
- `respond_permission/respond_question` 等方法 → 不再检查/关闭 ExpandedWindow，改为调用 JS `hideDetail()`

**删除：**
- `ExpandedWindow` 类（整个删除）
- `open_expanded_window()` 方法
- `on_expanded_closed()` 方法
- `_expanded_open` 标志及相关逻辑

### CSS 样式

从 `expanded.html` 迁移到 `island.html`：
- `.message-row` / `.message-bubble`（消息气泡）
- `.permission-card`（权限审批卡片）
- `.question-card`（提问选项卡片）
- `.empty-detail`（空状态）

新增：
- `#detail-view` 默认 `opacity: 0; display: none`
- `#detail-view.active` → `opacity: 1; display: block`
- `#list-view.active` / `#detail-view.active` 切换动画

### JS 迁移

从 `expanded.html` 迁移到 `island.html`：
- `markdownToHtml()` / `processInline()` / `escapeHtml()`（Markdown 渲染，如已有则跳过）
- `updateSessionDetail(data)` → 改为向 `#detail-content` 渲染
- `renderEvent()` / `addMessage()` / `addPermissionCard()` / `addQuestionCard()`
- `respondQuestion()` → 改用 `bridge.respondQuestion()`

新增：
- `showDetail()` → 切换到详情视图
- `hideDetail()` → 切换回列表视图

### 不在范围内

- 窗口尺寸/位置调整
- 动画时长变更
- 权限/提问交互逻辑变更
- 数据模型变更
