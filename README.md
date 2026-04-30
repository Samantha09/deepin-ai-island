# Deepin AI Island v1.0.0

一款专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具，以"屏幕顶部中央浮动胶囊"（灵动岛模式）作为核心 UI，让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

## 运行方式

```bash
# 确保依赖已安装
source .venv/bin/activate
pip install -r requirements.txt

# 启动 Island（连接 Claude Code 真实事件）
python island_ui/main.py

# 或使用 Mock 模拟事件测试 UI
python island_ui/main.py --source mock
```

## 交互说明

启动后，屏幕顶部中央将出现一个浮动胶囊：

1. **悬停胶囊** — 自动展开会话列表
2. **点击会话卡片** — 打开详情面板查看完整聊天记录
3. **权限审批** — 悬停会话卡片直接快捷审批（拒绝 / 允许），或在详情面板审批
4. **审批自动弹窗** — 新权限请求到来时自动弹出详情面板，5 秒后自动缩回
5. **会话排序** — 待审批会话置顶，运行中会话其次，已完成/空闲最后

## 快捷键

| 快捷键 | 作用 |
|--------|------|
| `Ctrl + Shift + I` | 手动展开/收起 Island |
| `Ctrl + Y` | 允许当前第一个待处理的权限请求 |
| `Ctrl + N` | 拒绝当前第一个待处理的权限请求 |
| `Esc` | 收起 Island（不处理事件） |
| `Ctrl + D` | 注入测试事件（调试模式） |

## 项目结构

```
deepin-ai-island/
├── island_ui/               # PySide6 桌面应用核心
│   ├── main.py              # 入口程序
│   ├── island_window.py     # 主窗口：无边框、置顶、QWebEngine
│   ├── web/                 # 前端页面（HTML/CSS/JS）
│   │   ├── island.html      # 主胶囊页面
│   │   └── expanded.html    # 详情面板页面
│   ├── claude_code_source.py # Claude Code Hook 事件源
│   ├── state_machine.py     # IDLE/COMPACT/EXPANDED 状态机
│   ├── event_source.py      # EventSource ABC + MockEventSource
│   ├── events.py            # 事件数据模型
│   └── session.py           # 会话模型
├── island_daemon/           # 守护进程（预留）
├── adapters/                # Agent 适配器（预留）
├── claude_hooks/            # Claude Code Hook 脚本
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

- **UI**: PySide6 (Qt6) + QWebEngine + QWebChannel
- **前端**: HTML/CSS/JS（内嵌，无需外部服务器）
- **Daemon**: Python 3.12+
- **IPC**: Unix Socket JSON
- **配置**: YAML

## 特性

- **Dynamic Island 风格动画** — 平滑的展开/收起高度与宽度动画，仿 macOS 灵动岛交互体验
- **会话列表与详情视图** — 实时监控多个 AI Agent 会话，点击进入详情查看完整事件流
- **快捷审批** — 悬停会话卡片即可直接 Allow / Deny，无需进入详情页
- **审批自动弹窗** — 权限请求到来时自动弹出详情面板，5 秒后自动缩回
- **工作概要** — 每个会话卡片展示最近 1-2 行工作摘要
- **主题系统** — 内置暗色主题
- **轮询兜底机制** — 针对部分 Linux 桌面环境 leaveEvent 不可靠的问题，使用定时轮询确保悬停状态准确

## 第二阶段预览

- Island Daemon 进程（asyncio Unix Socket）
- Plan Review（Markdown 渲染）
- 其他 Agent 支持（Codex、Gemini CLI）

## License

本项目采用 [MIT](LICENSE) 许可证开源。
