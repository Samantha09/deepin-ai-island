## Deepin AI Island v0.2.0

### 新增功能

#### AskUserQuestion 支持
- Socket Server 层新增提问事件解析与回复通道
- 主窗口新增问题回复桥接与处理逻辑
- 展开区域新增 Question Card 交互 UI
- 点击"需要回答"文本进入详情视图进行回答

#### 音效插件
- 新增 SoundPlugin 音效插件，支持新会话/权限请求/完成等事件的声音提示
- 默认配置增加 sound 段，支持音量调节
- 已完成会话 30 秒后自动变为 idle 并播放音效

#### 设置菜单
- 新增设置下拉菜单（设置按钮"..."）
- 支持清除已完成会话
- 支持音效开关与音量调节（持久化保存）
- 支持退出应用

#### 终端跳转
- 点击会话卡片直接跳转到对应的终端窗口
- 支持 tmux 会话识别与普通终端 TTY 回退检测
- 改进终端跳转逻辑，修复多窗口匹配问题

### UI/UX 改进

- **无抖动动画**：使用 `setMask` 实现丝滑流畅的悬停展开/收起动画，彻底消除抖动
- **悬停展开宽度**：从 380px 调整到 460px，内容展示更宽敞
- **Markdown 渲染增强**：expanded 窗口和悬停摘要均支持 Markdown 渲染
- **权限请求自动展开**：新权限请求到来时自动展开会话列表（非详情页），5 秒后自动缩回
- **多行对话摘要**：悬停会话卡片自动展开显示最近 3 行聊天记录摘要
- **单窗口详情视图**：详情面板交互与样式重构
- **状态同步优化**：轮 poll 正确识别 processing / busy / idle 状态，避免活跃会话误标为灰色

### Bug 修复

- 修复会话卡片点击无法打开详情及 question 显示问题
- 修复 AskUserQuestion 事件路由与交互响应
- 修复轮 poll 的 idle 不应覆盖 running 状态的问题
- 修复已结束会话不被 SessionStarted 重复标记为 running
- 修复 progress.updated 不再覆盖 completed 状态
- 修复首次启动未加载已有会话列表的问题
- 修复展开后无法收起的 bug
- 修复鼠标移开后强制清除权限通知展开状态
- 恢复 PermissionRequest 旧格式 `{"approved": true}` 兼容代码
- QuestionAsked 解析添加 data 顶层字段 fallback

### 测试

- 新增 SoundPlugin 单元测试
- 新增 clear_completed_sessions 和音效设置单元测试
- 新增 question.asked 状态变更测试

### 文档

- 完善 README，添加产品使用截图（紧凑模式 / 展开模式）
- 更新交互说明与项目结构
- 新增 Claude Code 选项选择支持设计文档与实现计划
- 新增一键清除已完成会话 + 设置菜单改造设计文档
- 明确 dev 为开发分支的工作规范

### 其他

- 将 `pkg/` 加入 `.gitignore` 防止误提交
- 统一 Bash 命令列表缩进格式，调整默认音量至 50
- 使用 monotonic 时钟替代 time.time

---

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
