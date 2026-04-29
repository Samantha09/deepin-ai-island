# Settings Drawer 设计文档

## 目标

为 AI Island 添加一个轻量设置抽屉（Settings Drawer），让用户无需离开当前工作流即可调整主题、动画开关、超时时间和窗口位置偏移。

## 方案选型

采用 **方案 C：轻量抽屉**。从 CompactPill 下方弹出紧凑设置卡片，轻量、不打断工作流，适合 Phase 1 MVP。

## 架构

```
IslandWindow (VBoxLayout)
├── CompactPill          ← 右上角新增 ⚙️ 设置按钮
├── SettingsDrawer       ← 轻量抽屉，默认隐藏
└── ExpandedPanel        ← 与抽屉互斥
```

## 交互流程

- 点击 pill 上的 **⚙️**：
  - drawer 隐藏 → 若 panel 展开则先收起 → drawer 滑出
  - drawer 显示 → drawer 收起（高度 → 0，动画结束后隐藏）
- **Esc**：若 drawer 展开 → 收起 drawer；否则按现有逻辑收起 panel
- drawer 与 panel **互斥**，不会同时展开

## 组件设计

### SettingsDrawer

- 宽度与 IslandWindow 一致（400px）
- 展开高度动态根据内容（~240–320px），最大不超过屏幕 40%
- 圆角 16px，背景 `#1e1e23`

内部布局（每行 `QHBoxLayout`）：

| 设置项 | 控件 | 默认值 |
|--------|------|--------|
| Theme | `QComboBox` | Dark |
| Animation | `QCheckBox` / Toggle | On |
| Compact timeout | `QSpinBox` + ms 标签 | 5000 |
| Position X | `QSpinBox` | 0 |
| Position Y | `QSpinBox` | 12 |

底部操作区：`[Reset defaults]` 按钮。

行高 40px，行间距 1px 分割线 `rgba(255,255,255,0.06)`。

### CompactPill 改动

- 右上角添加设置按钮（`QPushButton`，图标 `⚙️`，无边框，hover 变亮）
- 点击发射 `settings_clicked` 信号

## 数据流

```
user changes control
    ↓
SettingsDrawer.on_value_changed(key, value)
    ↓
Config.set(key, value) + Config.save()
    ↓
Config.config_changed signal
    ↓
IslandWindow / StateMachine / Animations update
```

### Config 单例

- 加载 `config/default.yaml`
- 提供 `get(key, default)`、`set(key, value)`、`save()`
- 变更时发射 `config_changed(key, value)` 信号
- YAML 解析失败时回退到默认配置，打印 warning

## 主题切换（最小实现）

- `Theme` 类：字典映射语义名到颜色值
- 先支持 3 套预设：**Dark**（当前配色）、**Light**、**Classic**
- 切换时遍历需要刷新的 widget（pill、panel、drawer、cards），重新 `setStyleSheet`
- 不追求完整 Token 体系，先把硬编码颜色抽到 `Theme.current()`，后续扩展

## 测试策略

- `tests/test_config.py`：YAML 读写、默认值回退、保存后文件内容验证
- `tests/test_settings_drawer.py`：UI 状态同步、重置按钮行为

## 文件变更预估

| 文件 | 动作 |
|------|------|
| `island_ui/settings_drawer.py` | 新增 |
| `island_ui/theme.py` | 新增 |
| `island_ui/config_manager.py` | 新增（Config 单例） |
| `island_ui/compact_pill.py` | 修改（添加设置按钮） |
| `island_ui/island_window.py` | 修改（集成 drawer、订阅 Config） |
| `island_ui/animations.py` | 修改（支持从 Config 读取动画开关） |
| `config/default.yaml` | 修改（新增主题、位置字段） |
| `tests/test_config.py` | 新增 |
| `tests/test_settings_drawer.py` | 新增 |
