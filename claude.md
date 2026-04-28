# Deepin AI Island — Claude 开发指南

## 项目概述

Deepin AI Island 是一款专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具。核心 UI 是"屏幕顶部中央浮动胶囊"（灵动岛模式），让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

**当前阶段**：Phase 1（MVP-UI），纯 UI 验证，使用模拟事件源驱动。

## 技术栈

- **UI**: PySide6 (Qt6)
- **Python**: 3.12+
- **配置**: YAML
- **虚拟环境**: `.venv/`

## 运行方式

```bash
source .venv/bin/activate
python island_ui/main.py
```

## 目录结构

```
island_ui/              # PySide6 桌面应用（第一阶段核心）
  main.py               # 入口程序，支持 --source mock|claude
  island_window.py      # 主窗口：无边框、置顶、焦点策略、视图切换
  compact_pill.py       # 顶部中央胶囊组件
  expanded_panel.py     # 展开面板：双视图（会话列表 / 事件详情）
  state_machine.py      # IDLE/COMPACT/EXPANDED 三状态机
  animations.py         # 动画工具
  event_source.py       # EventSource ABC + MockEventSource
  claude_code_source.py # Phase 2: Unix Socket 服务器 + 事件解析
  events.py             # 事件数据模型 + 序列化
  card_factory.py       # 事件类型 → 卡片工厂
  session.py            # Session 数据模型
  cards/                # 事件卡片
    base_card.py         # EventCard 基类
    permission_card.py   # 权限请求（允许/拒绝）
    question_card.py     # 问题（选项/输入框）
    progress_card.py     # 进度（暂未使用）
    session_list_item.py # 会话列表条目

claude_hooks/           # Phase 2: Claude Code 官方 hook
  install.py            # 安装/卸载 hook 到 ~/.claude/settings.json
  ai_island_hook.py     # 单一 hook 脚本：stdin 接事件 → Unix Socket → UI

island_daemon/          # 第三阶段：IPC 守护进程（预留空壳）
adapters/               # 第三阶段：Agent 适配器（预留空壳）
config/
  default.yaml          # 配置：动画开关、超时时间、位置
tests/                  # 单元测试
```

## 核心架构

### 事件流（第一阶段）

```
MockEventSource (QTimer 剧本)
  → event_received 信号
  → IslandWindow._on_event()
    → SessionStarted / SessionEnded → 更新会话列表
    → PermissionRequested / QuestionAsked → 创建 EventCard
  → StateMachine (状态转换)
  → UI 更新（COMPACT / EXPANDED / IDLE）
```

### 状态机

```
[IDLE] ──事件到达──► [COMPACT]
                        │
                        │ 鼠标悬停 / 点击 / 快捷键
                        ▼
                    [EXPANDED] ←──── 点击会话条目
                        │               │
                        │ Back按钮      │
                        ▼               ▼
                    [COMPACT]      事件详情视图
                        │
                        │ 5秒无新事件
                        ▼
                      [IDLE]
```

### 双视图设计

ExpandedPanel 支持两种视图：
1. **会话列表视图**：显示所有活跃会话的 SessionListItem，点击后切换到详情
2. **事件详情视图**：显示单个会话的事件卡片（PermissionCard / QuestionCard）

### 窗口策略

- 窗口标志：`FramelessWindowHint | WindowStaysOnTopHint | Tool`
- 背景：`QPalette` + `setAutoFillBackground(True)`，颜色 `#151519`
- **不用 `WA_TranslucentBackground`**：在 Linux 下会导致桌面壁纸透出
- **不用 `setMask`**：Wayland 不支持
- **不用 `paintEvent` 画背景**：在 FramelessWindow 上不可靠

## 关键类说明

### IslandWindow

主窗口。管理：
- 事件接收与分发（`_on_event`）
- 会话跟踪（`_sessions: dict[str, Session]`）
- 视图切换（会话列表 ↔ 事件详情）
- 状态机联动（展开/折叠/空闲）
- 快捷键和鼠标交互

**注意**：`leaveEvent` 使用 400ms 延迟定时器，避免鼠标在子控件间快速移动时误触发折叠。

### MockEventSource

模拟事件源。维护一个全局时间线 `_timeline: list[(float, Event)]`，按时间顺序推送事件。

当前剧本（3 个会话）：
- s1-claude: fix auth bug → permission → completed
- s2-codex: backend server → question → completed
- s3-gemini: optimize queries → permission → completed

### Session

会话数据模型：
- `id`, `name`, `agent`, `terminal`
- `status`: running / needs_attention / completed
- `events`: 该会话的所有事件列表
- `duration_text()`: 返回 "2m" / "1h" 等友好格式

### SessionListItem

会话列表条目组件。显示：
- 左侧状态圆点（蓝色=运行中，橙色=需要注意，绿色=完成）
- 任务名称 + 当前状态描述
- 右侧标签：Agent 名、终端名、运行时间

点击后发射 `clicked(session_id)` 信号。

## 样式规范

- 主背景色：`#151519`（窗口）、`#1e1e23`（面板/胶囊）
- 卡片背景：`rgba(255,255,255,0.05)` → 已改为 `#1e1e23`
- 文字：主文本 `#eeeeee`，副文本 `#888888`，标签 `#aaaaaa`
- 圆角：窗口 16px，面板 16px，卡片 14px，按钮 8px
- 强调色：允许 `#4CAF50`，拒绝/取消 `#FF5252`，信息 `#2196F3`

## 已知问题和限制

1. **窗口背景**：`QPalette` 方案在大部分 Linux 桌面环境下工作，但某些 compositor 仍可能添加阴影。如遇问题，可去掉窗口圆角，改直角矩形。
2. **焦点策略**：当前未使用 `WindowDoesNotAcceptFocus`，输入框可以正常获取焦点。如需严格不抢焦点，需额外处理。
3. **Wayland**：`setMask` 不支持，窗口圆角依赖 `QPalette` 和内部控件圆角。
4. **字体**：main.py 中设置 `_setup_font`，优先尝试 Noto Sans CJK SC / WenQuanYi Micro Hei。

## Phase 2：连接真实 Claude Code CLI

### 架构（对标 macOS vibe-notch）

```
Claude Code settings.json（~/.claude/settings.json）
  hooks.SessionStart       → ai_island_hook.py
  hooks.PermissionRequest  → ai_island_hook.py  (timeout=86400，保持连接等响应)
  hooks.PreToolUse         → ai_island_hook.py
  hooks.PostToolUse        → ai_island_hook.py
  hooks.Stop               → ai_island_hook.py

ai_island_hook.py
  stdin 读取 Claude Code 发来的 hook JSON
  → Unix Socket (/tmp/ai-island.sock) 发送给 AI Island
  → PermissionRequest 时阻塞等待 socket 回传决策
  → stdout 输出 {"decision": "allow"} 或 {"decision": "deny"} 给 Claude Code

AI Island UI
  SocketServerThread (QThread)      # 监听 /tmp/ai-island.sock
  ClaudeCodeEventSource             # 解析 hook JSON → Event 对象
  → PermissionCard 点击 Allow/Deny → respond_to_permission() → 写回 socket
```

### 安装 hook

```bash
python claude_hooks/install.py
# 然后重启 Claude Code
```

卸载：
```bash
python claude_hooks/install.py --uninstall
```

### 运行方式

```bash
# 使用模拟事件（开发测试）
python island_ui/main.py

# 使用真实 Claude Code 事件（需先安装 hook）
python island_ui/main.py --source claude
```

### 双向控制原理

当 Claude Code 触发 `PermissionRequest` hook 时：
1. hook 脚本通过 Unix Socket 把事件发给 AI Island
2. hook **保持 stdout 打开**，Claude Code 等待 hook 退出
3. AI Island 的 SocketServerThread **保持该 socket 连接**
4. UI 弹出 PermissionCard，用户点击 Allow / Deny
5. `ClaudeCodeEventSource.respond_to_permission()` 通过 socket 写回 `{"decision": "allow"}`
6. hook 脚本收到响应，输出给 Claude Code，Claude Code 继续执行

## 扩展指南

### 添加新的事件类型

1. 在 `events.py` 定义新的 `Event` 子类
2. 在 `card_factory.py` 添加映射
3. 在 `cards/` 新建对应的卡片子类
4. 在 `adapters/` 中解析生成该事件（第二阶段）

### 添加新的 Agent 适配器

1. 继承 `adapters/base.py` 中的 `AgentAdapter`
2. 实现 `start()`, `parse_event()`, `send_response()`
3. 在 `adapters/__init__.py` 注册

## 快捷键

| 快捷键 | 作用 |
|--------|------|
| `Ctrl+Shift+I` | 展开/收起 Island |
| `Ctrl+Y` | 允许首个权限请求 |
| `Ctrl+N` | 拒绝首个权限请求 |
| `Esc` | 收起 |
| `Ctrl+D` | 注入测试权限事件 |
