# Deepin AI Island 设计文档

## 1. 项目概述

Deepin AI Island 是一款专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具，参考 Vibe Island 的交互理念，以"屏幕顶部中央浮动胶囊"（灵动岛模式）作为核心 UI，让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

**项目定位**：完全独立于 FinBot 的新项目，专注于本地 AI Agent 监控。

## 2. 设计目标

1. **视觉还原**：深色磨砂玻璃质感的顶部浮动胶囊，展开/收缩动画流畅，不抢走编辑器焦点
2. **架构可扩展**：客户端-守护进程分离，新增 AI Agent 无需改动 UI 层
3. **完全本地**：无云端、无账号、无遥测，所有数据留在用户机器上
4. **渐进交付**：分阶段实现，第一阶段先验证 UI 和交互，第二阶段接入真实 Agent

## 3. 架构设计（分阶段交付）

### 3.1 分阶段策略

采用**分阶段交付，先 UI 后后端**的策略，核心原则是：**第一阶段就把事件模型和 UI 渲染边界锁死，第二阶段只换数据源**。

```
第一阶段（纯 UI 验证）
┌─────────────────────────────────────────┐
│              Island UI                   │
│  (PySide6 / Qt6)                        │
│  ├─ CompactPill + ExpandedPanel          │
│  ├─ EventCard 子类（Permission/Question） │
│  ├─ MockEventSource（模拟事件源）         │
│  └─ 状态机 + 动画系统                     │
└─────────────────────────────────────────┘

第二阶段（接入后端）
┌─────────────────────────────────────────┐
│              Island UI                   │
│  ├─ 所有 UI 模块复用，零改动              │
│  └─ SocketClient 替换 MockEventSource    │
└──────────────┬──────────────────────────┘
               │ Unix Socket / JSON IPC
               ▼
┌─────────────────────────────────────────┐
│           Island Daemon                  │
│  ├─ IPCServer (asyncio Unix Socket)      │
│  ├─ Session Manager                      │
│  ├─ EventBus                             │
│  └─ Response Handler                     │
└──────────────┬──────────────────────────┘
               │ stdin/stdout / files
               ▼
┌─────────────────────────────────────────┐
│            Hook Adapters                 │
│  ├─ ClaudeCodeAdapter（第二阶段）         │
│  ├─ CodexAdapter（预留）                 │
│  └─ GeminiCLIAdapter（预留）             │
└─────────────────────────────────────────┘
```

### 3.2 为什么分阶段？

| 维度 | 一次性完整实现 | 分阶段交付（本方案） |
|------|-------------|-------------------|
| 风险 | IPC/Daemon/Adapter 任一模块出问题，整个系统不可用 | UI 先独立跑通，降低初期挫败感 |
| 验证速度 | 需要配置完整环境才能看到效果 | 运行 `python main.py` 立刻看到灵动岛 |
| 架构腐化风险 | 急于联调可能牺牲边界清晰度 | 第一阶段就锁死事件模型，第二阶段只换数据源 |
| 迭代反馈 | 周期长，问题集中暴露 | 每阶段都有可演示的里程碑 |

## 4. 模块详解

### 4.1 Island UI (PySide6) — 第一阶段核心

**核心窗口类：**
- `IslandWindow`：无边框、置顶、穿透点击（非交互区域不抢焦点）
- `CompactPill`：顶部中央胶囊，显示 `{count} 个请求` + 活跃 agent 列表
- `ExpandedPanel`：向下展开的面板，最大高度限制为屏幕高度的 60%
- `EventCard` 基类 + 子类：`PermissionCard`, `AskQuestionCard`, `ProgressCard`

**动画系统：**
- 胶囊宽度根据内容动态调整（QPropertyAnimation on width）
- 面板高度从 0 展开到内容高度
- 新卡片滑入（translateY + opacity）
- 已处理卡片滑出并收缩

**焦点策略：**
- 窗口标志：`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.ToolTip | Qt.WindowDoesNotAcceptFocus`
- 当用户点击编辑器时，Island 不会抢夺焦点
- 例外：用户在 Island 内输入文字（如 QuestionCard 输入框）时临时接受焦点，输入完成后恢复

### 4.2 MockEventSource — 第一阶段数据源

- 实现 `EventSource` 抽象基类，定义 `event_received = Signal(dict)`
- `MockEventSource` 启动一个 `QTimer` 按剧本顺序推送事件：
  1. `session.started` — 模拟 Agent 启动
  2. `permission.requested` — 模拟权限请求
  3. `question.asked` — 模拟用户问题
  4. `progress.updated` — 模拟进度更新
  5. `session.ended` — 模拟结束
- 支持交互式调试：UI 界面上加「注入测试事件」隐藏调试按钮（Ctrl+D 触发）

### 4.3 第二阶段预留接口

**SocketClient**：
- 同样继承 `EventSource`，内部用 `QLocalSocket`（或 Python 标准库 `socket` + QThread）连接 Daemon 的 Unix Socket
- 协议完全复用 `events.py` 中的数据结构，JSON 序列化
- 替换时主窗口代码一行不改：`source = MockEventSource()` → `source = SocketClient()`

**Island Daemon**：
- `IPCServer`：Python `asyncio.start_unix_server()`，处理单 UI 连接，消息序列化 JSON，带心跳
- `Session`：代表一个 agent 进程的生命周期，包含状态、当前任务、待处理事件队列
- `EventBus`：内部发布-订阅，Adapter 发布事件，UI 订阅事件

**AgentAdapter 抽象基类**：
- `start(session: Session)` — 启动 agent 进程并注入 hooks
- `parse_event(raw: dict) -> Event` — 将原始 hook 数据解析为标准 Event
- `send_response(session: Session, response: Response)` — 将用户操作回传给 agent

**Claude Code Adapter（第二阶段实现）**：
- 通过 `CLAUDE_CODE_SETTINGS` 环境变量配置 hooks
- Hook 类型映射：
  - `permission_request` → `PermissionEvent`
  - `ask_user_question` → `QuestionEvent`
  - `plan_review` → `PlanEvent`
  - `command_start / command_finish` → `ProgressEvent`
- 响应回传：通过修改 hook 约定的文件或 stdout 协议

## 5. UI/UX 设计

### 5.1 状态机

```
[IDLE] ──事件到达──► [COMPACT]
                        │
                        │ 鼠标悬停 / 点击 / 快捷键
                        ▼
                    [EXPANDED]
                        │
                        │ 所有事件处理完毕，用户移开鼠标
                        ▼
                    [COMPACT]
                        │
                        │ 5秒无新事件
                        ▼
                      [IDLE]
```

### 5.2 事件卡片规范

所有卡片共享：
- 圆角 14px
- 背景 `rgba(255,255,255,0.05)`
- 内边距 14px
- 底部边距 10px
- 进入动画：`opacity 0→1`, `translateY -10px→0`, 时长 250ms, easing ease-out

**Permission Card：**
- 标题：小字灰色 `Permission Request`
- 正文：请求的具体操作（如 "Allow editing src/main.py?"）
- 操作区：两个按钮并排，「拒绝」左，「允许 ⌘Y」右（绿色强调）

**AskQuestion Card：**
- 标题：`Claude asks`
- 正文：问题内容
- 选项区：如果是多选，显示为垂直排列的选项卡片；如果是文本输入，显示单行输入框 + 提交按钮

### 5.3 快捷键

| 快捷键 | 作用 |
|--------|------|
| `⌘/Ctrl + Shift + I` | 手动展开/收起 Island |
| `⌘/Ctrl + Y` | 允许当前第一个待处理的权限请求 |
| `⌘/Ctrl + N` | 拒绝当前第一个待处理的权限请求 |
| `Esc` | 收起 Island（不处理事件） |
| `Ctrl + D` | 注入测试事件（调试模式） |

## 6. IPC 协议

所有消息为 JSON，格式如下：

```json
{
  "type": "event | response | heartbeat | command",
  "payload": {},
  "timestamp": 1714291200,
  "session_id": "uuid"
}
```

**事件类型（Daemon → UI）：**
- `session.started` - Agent 会话开始
- `session.ended` - Agent 会话结束
- `permission.requested` - 需要用户审批权限
- `question.asked` - 需要用户回答问题
- `plan.review` - Plan 需要审阅
- `progress.updated` - 进度更新

**响应类型（UI → Daemon）：**
- `permission.resolved` - 允许/拒绝
- `question.answered` - 用户选择的答案
- `plan.approved` / `plan.rejected` - Plan 审阅结果

## 7. 扩展点

### 7.1 添加新的 AI Agent

只需实现 `AgentAdapter` 接口：
1. 新建 `adapters/<agent_name>.py`
2. 继承 `AgentAdapter`，实现 `start()`, `parse_event()`, `send_response()`
3. 在 `adapters/__init__.py` 注册
4. UI 层无需任何改动

### 7.2 添加新的事件类型

1. 在 `events.py` 定义新的 `Event` 子类
2. 在相关 `AgentAdapter` 中解析生成该事件
3. 在 UI 层新建对应的 `EventCard` 子类
4. 在 `CardFactory` 中注册映射

### 7.3 支持新的桌面环境

Island UI 的核心逻辑不依赖 Deepin 特有 API，但以下部分可能需要适配：
- 通知回退：Deepin 下使用 D-Bus 通知接口，GNOME/KDE 下使用 libnotify
- 窗口管理器特殊行为：X11 vs Wayland 的焦点/置顶策略
- 终端跳转：X11 用 `xdotool`/`wmctrl`，Wayland 需要特定 compositor 的 API

## 8. 第一阶段范围（MVP-UI）

**仅实现 Island UI + MockEventSource**：

1. **Island UI**
   - 紧凑胶囊 + 展开面板
   - Permission Request 卡片（允许/拒绝按钮）
   - AskUserQuestion 卡片（选项按钮 / 输入框）
   - Progress 卡片（进度条 / 状态文本）
   - 基本展开/收缩动画
   - 快捷键支持
   - 模拟事件源驱动

2. **暂不实现（第二阶段）**
   - Island Daemon 进程
   - Claude Code Hook Adapter
   - Unix Socket 真实 IPC
   - Plan Review（Markdown 渲染）
   - 多 Session 同时监控
   - 用量追踪
   - WebSocket 远程监控
   - 音效提醒
   - 其他 Agent 支持

## 9. 技术栈

| 层级 | 技术 | 理由 |
|------|------|------|
| UI | PySide6 (Qt6) | Deepin DDE 基于 Qt，风格原生一致；QPropertyAnimation 动画成熟 |
| Daemon | Python 3.11+ | 开发速度快，asyncio 适合 I/O 密集型事件处理 |
| IPC | Unix Socket（本地）| 低延迟，无网络栈开销；WebSocket 协议作为远程预留 |
| 配置 | YAML | 用户可读的 hooks 配置和全局设置 |
| 打包 | PyInstaller / 原生 deb | Deepin 用户习惯 deb 包，也可用 PyInstaller 做单文件分发 |

## 10. 数据流（第一阶段）

```
用户运行 python island_ui/main.py
    │
    ▼
IslandWindow 初始化，加载 CompactPill + ExpandedPanel
    │
    ▼
MockEventSource 启动 QTimer，按剧本推送事件
    │
    ▼
IslandWindow 从 IDLE 变为 COMPACT/EXPANDED，渲染 EventCard
    │
    ▼
用户点击「允许」→ 卡片标记为已处理 → 淡出动画
    │
    ▼
所有事件处理完毕 → 回到 COMPACT → 5秒后 IDLE
```

## 11. 目录结构（第一阶段）

```
deepin-ai-island/
├── island_ui/               # PySide6 桌面应用
│   ├── main.py
│   ├── island_window.py     # IslandWindow + 焦点/窗口管理
│   ├── compact_pill.py      # 胶囊组件
│   ├── expanded_panel.py    # 展开面板 + 滚动
│   ├── cards/
│   │   ├── base_card.py     # EventCard 基类 + 动画
│   │   ├── permission_card.py
│   │   └── question_card.py
│   ├── animations.py        # 动画工具/缓动函数
│   ├── event_source.py      # EventSource 抽象类 + MockEventSource
│   └── events.py            # 事件数据模型（IPC 协议）
├── island_daemon/           # 第二阶段启用，第一阶段只有空壳接口
│   ├── ipc_server.py        # asyncio UnixSocket server（预留）
│   ├── session.py           # Session 模型（预留）
│   └── events.py            # 复用 UI 层定义（或 symlink）
├── adapters/
│   ├── base.py              # AgentAdapter 抽象基类
│   └── claude_code.py       # 第一阶段：空壳 + 接口注释
├── config/
│   └── default.yaml         # 窗口位置、动画开关、超时时间
├── requirements.txt         # PySide6, pyyaml
└── README.md
```

## 12. 配置（default.yaml）

```yaml
island:
  position: top-center
  animation_enabled: true
  compact_timeout_ms: 5000
  expanded_max_height_ratio: 0.6
debug:
  mock_events_enabled: true  # 第一阶段 true，第二阶段 false
```

## 13. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Qt 无边框窗口在 Deepin 下置顶/焦点行为异常 | 早期 POC 验证窗口标志组合，准备 X11 原生 fallback |
| Claude Code hooks 协议不稳定 | 隔离在 Adapter 层，协议变化时只改一处 |
| 动画性能在低端机器上卡顿 | 提供配置项关闭动画，使用即时状态切换 |
| 多显示器支持复杂 | 第一阶段先支持主显示器，后续检测鼠标所在屏幕 |
| 第一阶段无真实数据源，架构边界可能不够清晰 | MockEventSource 严格遵循 IPC 协议结构，第二阶段只换传输层 |
