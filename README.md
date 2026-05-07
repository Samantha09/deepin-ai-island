# Deepin AI Island v1.0.0

一款专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具，以"屏幕顶部中央浮动胶囊"（灵动岛模式）作为核心 UI，让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

## 功能特性

- **Dynamic Island 风格动画** — 使用 `setMask` + CSS `transition` 实现丝滑流畅的展开/收起动画，彻底消除抖动
- **实时会话监控** — 自动发现 Claude Code 会话，启动时立即加载已有活跃会话
- **多行对话摘要** — 悬停会话卡片自动展开显示最近 3 行聊天记录摘要
- **Markdown 渲染** — 支持在详情面板中渲染 Markdown 格式的消息内容
- **状态点脉冲动画** — 运行中会话的状态指示器带有呼吸灯脉冲效果
- **快捷审批** — 悬停会话卡片即可直接 Allow / Deny，无需进入详情页
- **审批自动弹窗** — 新权限请求到来时自动展开列表（非详情页），5 秒后自动缩回
- **智能排序** — 待审批会话置顶，运行中会话其次，已完成/空闲最后
- **实时状态同步** — 准确反映 AI 空闲、处理中、等待审批等状态
- **会话名称** — 自动使用工作目录名称作为会话标识，便于区分多个会话

## 安装方式

### 方式一：deb 包安装（推荐）

下载 `deepin-ai-island_v1.0.0_amd64.deb`，双击安装或使用命令：

```bash
sudo dpkg -i deepin-ai-island_v1.0.0_amd64.deb
```

安装后从启动器运行 "AI Island"。

### 方式二：源码运行

```bash
# 1. 克隆仓库
cd deepin-ai-island

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动 AI Island（连接 Claude Code 真实事件）
python island_ui/main.py
```

### 方式三：直接运行可执行文件

解压 `deepin-ai-island_v1.0.0_linux_x64.tar.gz` 后运行：

```bash
./deepin-ai-island
```

## 运行模式

### Claude Code 模式（默认）

自动连接本地运行的 Claude Code 会话，通过 Unix Socket (`/tmp/ai-island.sock`) 接收实时事件。

**前置条件：**
- 已安装 Claude Code CLI
- `~/.claude/settings.json` 中已配置 Hook 脚本路径

### Mock 模式（UI 测试）

无需启动 Claude Code，自动模拟各种事件序列，用于验证 UI 动画和交互：

```bash
source .venv/bin/activate
python island_ui/main.py --source mock
```

Mock 模式会自动模拟：会话创建、权限请求、用户输入、AI 回复、状态变化等场景。

## 交互说明

启动后，屏幕顶部中央将出现一个浮动胶囊：

1. **悬停胶囊** — 自动展开会话列表，显示最近 3 行聊天记录摘要
2. **点击会话卡片** — 打开详情面板查看完整 Markdown 渲染的聊天记录
3. **权限审批** — 悬停会话卡片直接快捷审批（拒绝 / 允许），或在详情面板审批
4. **审批自动弹窗** — 新权限请求到来时自动展开列表，5 秒后自动缩回
5. **快捷键** — `Ctrl + Shift + I` 手动展开/收起，`Ctrl + Y` 允许首个权限，`Ctrl + N` 拒绝，`Esc` 收起

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
├── island_ui/                 # PySide6 桌面应用核心
│   ├── main.py                # 入口程序
│   ├── island_window.py       # 主窗口：无边框、置顶、QWebEngine、setMask 动画
│   ├── web/                   # 前端页面（HTML/CSS/JS）
│   │   ├── island.html        # 主胶囊页面（CSS transition 动画）
│   │   └── expanded.html      # 详情面板页面（Markdown 渲染）
│   ├── claude_code_source.py  # Claude Code Hook 事件源（Unix Socket + 轮询）
│   ├── state_machine.py       # IDLE/COMPACT/EXPANDED 状态机
│   ├── event_source.py        # EventSource ABC + MockEventSource
│   ├── events.py              # 事件数据模型
│   └── session.py             # 会话模型（状态转换、事件聚合）
├── island_daemon/             # 守护进程（预留）
├── adapters/                  # Agent 适配器（预留）
├── claude_hooks/              # Claude Code Hook 脚本
│   └── ai_island_hook.py      # Hook 主脚本
├── config/
│   └── default.yaml           # 窗口位置、动画开关、超时时间
├── tests/                     # 单元测试
├── requirements.txt
├── build_deb.sh               # deb 打包脚本
├── build.py                   # PyInstaller 打包脚本
└── README.md
```

## 技术栈

- **UI 框架**: PySide6 (Qt6) + QWebEngineView + QWebChannel
- **前端**: 原生 HTML5 / CSS3 / JavaScript（内嵌，无需外部服务器）
- **动画**: Qt `setMask(QRegion)` + CSS `transition` + `cubic-bezier(0.22, 1, 0.36, 1)`
- **运行时**: Python 3.12+
- **IPC**: Unix Domain Socket（JSON 协议）
- **配置**: YAML

## 开发调试

### 检查 Hook 状态

```bash
# 检查 hooks 是否注册
python3 -m json.tool ~/.claude/settings.json | grep -A 3 ai_island_hook

# 检查 socket 文件是否存在且被监听
ls -la /tmp/ai-island.sock
lsof /tmp/ai-island.sock
```

### 手动注入测试事件

无需启动 Claude Code，直接通过 Unix Socket 注入事件：

```python
import json, socket

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/tmp/ai-island.sock")
sock.sendall(json.dumps({
    "event": "UserPromptSubmit",
    "session_id": "test-001",
    "payload": {"prompt": "帮我修一个bug"}
}).encode())
sock.close()
```

### 运行测试

```bash
source .venv/bin/activate
python tests/test_events.py
python tests/test_event_source.py
python tests/test_state_machine.py
```

## 常见问题

| 现象 | 排查方向 |
|------|---------|
| 只显示 "idle" | 检查 `~/.claude/settings.json` 是否含 hooks 配置；Claude Code 是否重启 |
| "暂无聊天记录" | 检查 `_build_summary` 是否过滤掉了所有事件；确认事件类型映射正确 |
| 悬停不展开 | 检查 `enterEvent` / `mouseMoveEvent`；确认 `_expand_area.setVisible(True)` 被调用 |
| 动画抖动 | 已使用 `setMask` 方案根治，如仍抖动请检查显卡驱动或禁用桌面特效 |

## 第二阶段预览

- Island Daemon 进程（asyncio Unix Socket）
- Plan Review（Markdown 渲染增强）
- 其他 Agent 支持（Codex、Gemini CLI）

## License

本项目采用 [MIT](LICENSE) 许可证开源。

Last checked: 2026-05-07
