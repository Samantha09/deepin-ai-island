## Deepin AI Island v1.0.0

专为 Linux（Deepin/DDE）打造的 AI Agent 监控工具。以屏幕顶部中央浮动胶囊（灵动岛模式）作为核心 UI，让用户在 AI Agent 工作时无需切换终端即可监控进度、批准操作和回答问题。

---

### ✨ 核心功能

- **灵动岛风格 UI** — PySide6 + QWebEngine 实现，悬停自动展开，平滑高度/宽度动画
- **多会话实时监控** — 同时追踪多个 Claude Code 会话，按优先级排序（待审批 > 运行中 > 其他）
- **快捷审批** — 悬停会话卡片即可直接 Allow / Deny，无需进入详情页
- **审批自动弹窗** — 新权限请求到来时自动弹出详情面板，5 秒后自动缩回
- **工作概要** — 每个会话卡片展示最近 1-2 行工作摘要（You: ... / AI: ...）
- **系统托盘** — 托盘区常驻图标，右键菜单支持显示/退出
- **Claude Code 集成** — Unix Socket 实时接收 Hook 事件，双向响应权限请求

---

### 📦 安装

```bash
# 下载本页附件 deepin-ai-island_1.0.0_amd64.deb
sudo dpkg -i deepin-ai-island_1.0.0_amd64.deb
```

依赖：`libgl1`, `libxkbcommon0`（Deepin 20/23 默认已包含）

---

### 🚀 运行

```bash
# 连接 Claude Code 真实事件（默认）
deepin-ai-island

# 或使用 Mock 模拟事件测试 UI
deepin-ai-island --source mock
```

---

### ⌨️ 快捷键

| 快捷键 | 作用 |
|--------|------|
| `Ctrl + Shift + I` | 手动展开/收起 Island |
| `Ctrl + Y` | 允许当前第一个待处理的权限请求 |
| `Ctrl + N` | 拒绝当前第一个待处理的权限请求 |
| `Esc` | 收起 Island |

---

### 🔧 技术栈

- **UI**: PySide6 (Qt6) + QWebEngine + QWebChannel
- **IPC**: Unix Socket JSON
- **配置**: YAML
- **Python**: 3.12+

---

### 📎 附件

- `deepin-ai-island_1.0.0_amd64.deb` — Deepin/DEB 系安装包（216 MB）

---

### 📝 许可证

[MIT](LICENSE)
