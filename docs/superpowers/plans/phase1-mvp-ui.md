# Phase 1: MVP-UI 实施计划

## 目标
实现 Deepin AI Island 的第一阶段：纯 UI 验证，包含灵动岛窗口、事件卡片、模拟事件源和状态机。

## 实施任务（15个步骤）

### Task 1: 项目脚手架 + 依赖安装
- 创建目录结构：`island_ui/`, `island_ui/cards/`, `island_daemon/`, `adapters/`, `config/`
- 创建 `requirements.txt`（PySide6, pyyaml）
- 安装依赖
- 创建 `.gitignore`

### Task 2: 事件数据模型 (events.py)
- 定义 `Event` 基类（dataclass）：`type`, `payload`, `timestamp`, `session_id`
- 定义事件子类：`SessionStarted`, `SessionEnded`, `PermissionRequested`, `QuestionAsked`, `ProgressUpdated`
- 定义响应类：`PermissionResolved`, `QuestionAnswered`
- 提供 `event_from_dict()` / `event_to_dict()` 序列化
- **测试**：验证序列化/反序列化

### Task 3: EventSource 抽象基类 + MockEventSource
- `EventSource` 继承 `QObject`，定义 `event_received = Signal(dict)`
- `MockEventSource`：用 `QTimer` 按剧本推送事件
- 剧本：`session.started` → `permission.requested` → `question.asked` → `progress.updated` → `session.ended`
- **测试**：验证信号发射和事件内容

### Task 4: 动画工具模块 (animations.py)
- `FadeSlideInAnimation`：opacity 0→1, translateY -10→0, 250ms, ease-out
- `HeightAnimation`：高度从 0 到目标值
- `WidthAnimation`：胶囊宽度动态调整
- **测试**：验证动画参数配置

### Task 5: BaseCard 事件卡片基类
- `EventCard` 继承 `QFrame`
- 样式：圆角 14px，背景 rgba(255,255,255,0.05)，内边距 14px，底部边距 10px
- 进入动画：使用 FadeSlideInAnimation
- 提供 `mark_resolved()` 方法，触发出场动画
- **测试**：验证样式和动画触发

### Task 6: CompactPill 紧凑胶囊
- `CompactPill` 继承 `QFrame`
- 显示：请求计数 + 活跃 agent 列表
- 样式：深色磨砂玻璃质感，圆角胶囊形状
- 支持点击展开
- **测试**：验证内容更新和点击信号

### Task 7: PermissionCard 权限请求卡片
- 继承 `EventCard`
- 布局：标题（Permission Request，小字灰色）+ 正文 + 双按钮
- 按钮：「拒绝」左（⌘N），「允许 ⌘Y」右（绿色）
- 点击后发射 `resolved` 信号，带 `approved: bool`
- **测试**：验证按钮点击信号

### Task 8: QuestionCard 问题卡片
- 继承 `EventCard`
- 布局：标题（Claude asks）+ 正文 + 输入区
- 多选模式：垂直排列的选项按钮
- 文本输入模式：单行输入框 + 提交按钮
- 发射 `answered` 信号，带答案内容
- **测试**：验证输入和选项选择

### Task 9: ProgressCard 进度卡片
- 继承 `EventCard`
- 布局：标题 + 进度条（QProgressBar）+ 状态文本
- 进度条样式：适配深色主题
- **测试**：验证进度更新

### Task 10: ExpandedPanel 展开面板
- `ExpandedPanel` 继承 `QWidget`
- 垂直布局的滚动区域（QScrollArea）
- 最大高度：屏幕高度的 60%
- 卡片容器，支持动态添加/移除卡片
- **测试**：验证滚动和高度限制

### Task 11: CardFactory 卡片工厂
- 根据事件类型创建对应卡片：`PermissionCard`, `QuestionCard`, `ProgressCard`
- 统一事件到卡片的映射
- **测试**：验证工厂创建正确类型

### Task 12: 状态机 (state_machine.py)
- `IslandStateMachine` 继承 `QObject`
- 状态：`IDLE`, `COMPACT`, `EXPANDED`
- 转换：
  - `IDLE` → `COMPACT`：事件到达
  - `COMPACT` → `EXPANDED`：鼠标悬停/点击/快捷键
  - `EXPANDED` → `COMPACT`：所有事件处理完毕 + 用户移开鼠标
  - `COMPACT` → `IDLE`：5秒无新事件
- 发射 `state_changed` 信号
- **测试**：验证状态转换逻辑

### Task 13: IslandWindow 主窗口集成
- `IslandWindow` 继承 `QMainWindow`
- 窗口标志：`FramelessWindowHint | WindowStaysOnTopHint | ToolTip | WindowDoesNotAcceptFocus`
- 无边框、置顶、穿透点击
- 集成 `CompactPill` + `ExpandedPanel`
- 连接 `EventSource` → `StateMachine` → UI 更新
- 位置：屏幕顶部中央
- **测试**：验证窗口标志和位置

### Task 14: 快捷键 + 调试模式
- 全局快捷键注册：`⌘/Ctrl + Shift + I`（展开/收起）
- 快捷键：`⌘/Ctrl + Y`（允许）、`⌘/Ctrl + N`（拒绝）、`Esc`（收起）
- `Ctrl + D`：注入测试事件（调试按钮）
- **测试**：验证快捷键响应

### Task 15: main.py 入口 + 配置加载
- `main.py`：QApplication 初始化，加载 `config/default.yaml`
- 创建 `IslandWindow` + `MockEventSource`
- 支持 `--debug` 参数
- **集成测试**：运行 `python main.py` 验证端到端

## 文件清单
```
deepin-ai-island/
├── island_ui/
│   ├── main.py
│   ├── island_window.py
│   ├── compact_pill.py
│   ├── expanded_panel.py
│   ├── state_machine.py
│   ├── animations.py
│   ├── event_source.py
│   ├── events.py
│   ├── card_factory.py
│   └── cards/
│       ├── __init__.py
│       ├── base_card.py
│       ├── permission_card.py
│       ├── question_card.py
│       └── progress_card.py
├── island_daemon/
│   ├── __init__.py
│   ├── ipc_server.py  (空壳)
│   └── session.py     (空壳)
├── adapters/
│   ├── __init__.py
│   ├── base.py        (空壳)
│   └── claude_code.py (空壳)
├── config/
│   └── default.yaml
├── tests/
│   ├── __init__.py
│   ├── test_events.py
│   ├── test_event_source.py
│   ├── test_state_machine.py
│   └── test_cards.py
├── requirements.txt
└── .gitignore
```

## 验收标准
- [ ] 运行 `python island_ui/main.py` 弹出顶部胶囊
- [ ] 胶囊自动从 IDLE → COMPACT → EXPANDED 展开
- [ ] 显示 PermissionCard、QuestionCard、ProgressCard
- [ ] 点击「允许/拒绝」卡片淡出
- [ ] 所有事件处理完毕后 5 秒回到 IDLE
- [ ] 快捷键 ⌘Shift+I 可手动展开/收起
- [ ] Ctrl+D 可注入测试事件
