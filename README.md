# Deepin AI Island

一款专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具，以"屏幕顶部中央浮动胶囊"（灵动岛模式）作为核心 UI，让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

## 第一阶段（MVP-UI）

当前版本为纯 UI 验证阶段，使用模拟事件源驱动，无需配置真实 Agent 即可体验完整交互。

### 运行方式

```bash
# 确保依赖已安装
source .venv/bin/activate
pip install -r requirements.txt

# 启动 Island
python island_ui/main.py
```

### 交互说明

启动后，屏幕顶部中央将出现一个浮动胶囊，按以下剧本自动演示：

1. **SessionStarted** — 胶囊显示 "1 request"
2. **PermissionRequested** — 展开面板，显示权限请求卡片（Allow / Deny）
3. **QuestionAsked** — 显示问题卡片，提供选项按钮
4. **ProgressUpdated** ×2 — 显示进度卡片，带进度条
5. **SessionEnded** — 所有事件处理完毕后 5 秒回到 IDLE

### 快捷键

| 快捷键 | 作用 |
|--------|------|
| `Ctrl + Shift + I` | 手动展开/收起 Island |
| `Ctrl + Y` | 允许当前第一个待处理的权限请求 |
| `Ctrl + N` | 拒绝当前第一个待处理的权限请求 |
| `Esc` | 收起 Island（不处理事件） |
| `Ctrl + D` | 注入测试事件（调试模式） |

### 鼠标交互

- **悬停胶囊/面板** — 自动展开
- **点击胶囊** — 展开/收起切换
- **点击按钮** — 处理对应事件卡片

## 项目结构

```
deepin-ai-island/
├── island_ui/               # PySide6 桌面应用（第一阶段核心）
│   ├── main.py              # 入口程序
│   ├── island_window.py     # 主窗口：无边框、置顶、焦点策略
│   ├── compact_pill.py      # 顶部中央胶囊组件
│   ├── expanded_panel.py    # 展开面板 + 滚动区域
│   ├── state_machine.py     # IDLE/COMPACT/EXPANDED 状态机
│   ├── animations.py        # 淡入淡出、滑动、高度/宽度动画
│   ├── event_source.py      # EventSource ABC + MockEventSource
│   ├── events.py            # 事件数据模型 + 序列化
│   ├── card_factory.py      # 事件 → 卡片工厂
│   └── cards/               # 事件卡片
│       ├── base_card.py     # EventCard 基类 + 动画
│       ├── permission_card.py
│       ├── question_card.py
│       └── progress_card.py
├── island_daemon/           # 第二阶段：IPC 守护进程（预留空壳）
├── adapters/                # 第二阶段：Agent 适配器（预留空壳）
├── config/
│   └── default.yaml         # 窗口位置、动画开关、超时时间
├── tests/                   # 单元测试
├── requirements.txt
└── README.md
```

## 测试

```bash
source .venv/bin/activate
python tests/test_events.py
python tests/test_event_source.py
python tests/test_state_machine.py
```

## 技术栈

- **UI**: PySide6 (Qt6)
- **Daemon**: Python 3.12+（第二阶段启用 asyncio）
- **IPC**: Unix Socket JSON（第二阶段）
- **配置**: YAML

## 第二阶段预览

- Island Daemon 进程（asyncio Unix Socket）
- Claude Code Hook Adapter
- Plan Review（Markdown 渲染）
- 多 Session 同时监控
- 其他 Agent 支持（Codex、Gemini CLI）
