# Claude Code 选项选择支持

## 背景

Claude Code 在交互中会通过 `AskUserQuestion` 向用户展示选项（如选择库、确认方案等）。目前 AI Island 收到 `question.asked` 事件后只以 "❓ 问题文本" 的形式显示为普通聊天消息，不支持选项选择或自定义输入。

## 目标

在悬停展开区域新增交互式 Question Card，支持：
1. 展示 Claude Code 给出的选项列表
2. 点击选项直接回复
3. "其他..." 选项展开输入框，支持自定义文本输入
4. 回复结果通过 Hook 回传给 Claude Code

## 设计

### 事件流

完整的问答交互链路，与权限审批对称：

```
Claude Code → Hook → Unix Socket → AI Island (claude_code_source.py)
    → island_window.py → expanded.html (Question Card)

用户选择 → JS Bridge → island_window.py → Unix Socket → Hook → Claude Code
```

**Hook 层**：
- 新增对提问事件的拦截，识别 Claude Code 的 `AskUserQuestion` 场景
- 将 `question.asked` 事件通过 Socket 发送给 AI Island，payload 包含 `question`、`options`、`tool_use_id`
- 发出后设置超时等待回复（与权限审批一致，最长 24 小时）
- 收到 `question.answered` 后将答案返回 Claude Code
- 超时返回空字符串，Claude Code 回退到终端交互

**AI Island 内部**：
1. `claude_code_source.py`：解析 `question.asked` 事件 → 创建 `QuestionAsked` 对象
2. `island_window.py`：将事件存入 session，推送到前端；处理回复回调
3. `expanded.html`：渲染 Question Card，处理用户交互
4. 用户操作 → Bridge 回调 → `island_window.py` → Socket → Hook

### 前端交互

**Question Card 结构**（仿照 permission-card）：

```
┌─────────────────────────────────┐
│  ❓ 你希望使用哪个库？           │
│                                 │
│  ┌───────────────────────────┐  │
│  │  React                    │  │  ← 选项按钮
│  ├───────────────────────────┤  │
│  │  Vue                      │  │
│  ├───────────────────────────┤  │
│  │  Angular                  │  │
│  ├───────────────────────────┤  │
│  │  其他...              ✎   │  │  ← 点击展开输入框
│  └───────────────────────────┘  │
│                                 │
│  ┌─────────────────────────┐    │  ← 展开后出现
│  │ 请输入...           发送 │    │
│  └─────────────────────────┘    │
└─────────────────────────────────┘
```

**交互逻辑**：
- 点击普通选项 → 直接回传选项文本，卡片变为已回答状态（灰色 + 显示选择结果）
- 点击"其他..." → 展开输入框，输入后点"发送"回传自定义文本
- 未回答时：蓝色边框视觉提示
- 已回答后：卡片变为已完成状态

**样式**：
- 复用 permission-card 整体风格（圆角、半透明背景）
- 用蓝色调区分（权限是橙色/黄色）
- 选项按钮样式参考权限按钮

### 数据模型

已有数据类无需修改：
- `QuestionAsked`（events.py）：包含 `question`、`options`、`session_id`
- `QuestionAnswered`（events.py）：包含 `answer`、`session_id`

需新增字段：`tool_use_id` 到 `QuestionAsked.payload`，用于关联回复。

### Mock 测试支持

在 mock source 中新增 `question.asked` 事件的模拟剧本，包含选项列表，方便 UI 开发验证。

### 涉及文件

| 文件 | 改动 |
|------|------|
| `claude_hooks/ai_island_hook.py` | 新增提问事件拦截与回复处理 |
| `island_ui/claude_code_source.py` | 新增 `question.asked` 事件解析和回复发送 |
| `island_ui/island_window.py` | 新增 `respond_question` 方法、Bridge 回调 |
| `island_ui/web/expanded.html` | 新增 Question Card HTML/CSS/JS |
| `island_ui/mock_source.py` | 新增模拟提问事件 |

### 不在范围内

- 独立弹窗或灵动岛本体上的选项 UI
- 选项的持久化存储或历史记录
- 多级嵌套选项或条件选项
