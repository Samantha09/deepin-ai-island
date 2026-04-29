# AI Island UI 全面重构设计文档

> 目标：建立统一的组件体系和主题 token，彻底消除硬编码样式，提升视觉一致性和交互体验。

---

## 架构

```
island_ui/
├── theme.py                    # 扩展 Theme/ThemePreset + 完整 Token 体系
├── components/                 # 新增基础组件包
│   ├── __init__.py
│   ├── base_row.py             # 可 hover 的圆角行容器（enterEvent/leaveEvent）
│   ├── menu_row.py             # 图标 + 标签 + 右侧控件的行
│   ├── toggle_row.py           # 开关行（绿色指示点 + On/Off 标签）
│   ├── menu_divider.py         # 分隔线（rgba(255,255,255,0.08)）
│   ├── styled_button.py        # 统一按钮（primary / secondary / ghost / danger）
│   └── icon_label.py           # 文本图标占位（16px 等宽）
├── cards/
│   ├── base_card.py            # Theme-aware，统一入场/退场动画
│   ├── permission_card.py      # 使用 styled_button + theme token
│   ├── question_card.py        # 使用 styled_button + theme token
│   └── session_list_item.py    # 使用 theme token，保持 hover 效果
├── compact_pill.py             # Theme-aware，消除硬编码色值
├── expanded_panel.py           # Theme-aware，消除硬编码色值
├── settings_drawer.py          # 重写为 MenuRow 列表风格
└── island_window.py            # 最小改动，接入新 theme token
```

---

## 主题 Token 体系（参考 Vibe-Island TerminalColors）

所有颜色通过语义名引用，禁止任何文件出现硬编码 hex。

| Token | 暗色值 | 说明 |
|-------|--------|------|
| `surface` | `#151519` | 最底层窗口背景 |
| `surface_panel` | `rgba(30,30,35,1)` | 面板背景（保持与现有接近） |
| `surface_card` | `rgba(255,255,255,0.05)` | 卡片背景 |
| `surface_card_hover` | `rgba(255,255,255,0.08)` | 卡片/行 hover |
| `surface_control` | `rgba(255,255,255,0.06)` | 输入框、按钮背景 |
| `surface_control_hover` | `rgba(255,255,255,0.10)` | 控件 hover |
| `text_primary` | `#eeeeee` | 主文本 |
| `text_secondary` | `#888888` | 次要文本 |
| `text_muted` | `rgba(255,255,255,0.4)` | 禁用/辅助文本（dim） |
| `text_inverse` | `#000000` | 亮色按钮上的文字 |
| `border` | `rgba(255,255,255,0.08)` | 边框、divider |
| `accent_green` | `#66bf73` | 成功、允许、On 状态 |
| `accent_amber` | `#ffb300` | 警告、等待中 |
| `accent_red` | `#ff4d4d` | 拒绝、错误、危险 |
| `accent_blue` | `#6699ff` | 信息、下载、进行中 |
| `accent_cyan` | `#00cccc` | 次要信息 |
| `accent_magenta` | `#cc66cc` | 高亮 |
| `divider` | `rgba(255,255,255,0.08)` | 分隔线 |

Light/Classic 主题相应调整（保持语义不变，只改数值）。

### Theme API 扩展

```python
class Theme:
    def current(self) -> dict[str, str]: ...
    def color(self, key: str) -> str: ...  # 新增：安全取值，缺失返回 ""
    def css(self, key: str, alpha: float | None = None) -> str: ...  # 新增：支持 rgba 变体
```

---

## 基础组件

### BaseRow（QFrame）

所有设置行的基类。

- 固定高度 40px（或自适应内容）
- `border-radius: 8px`
- 默认背景透明
- hover 时背景变为 `surface_card_hover`
- 通过 `enterEvent`/`leaveEvent` 切换 `self._hovered` 状态并更新 styleSheet
- 内边距：`padding: 10px 12px`

### MenuRow（BaseRow）

用于设置抽屉中的普通行。

```
┌────────────────────────────────────────┐
│ [icon]  Label                    [ctrl] │
└────────────────────────────────────────┘
```

- 左侧：16px 宽图标占位（QLabel，12px 字体）
- 中间：13px medium 标签文字，颜色 `text_primary`
- 右侧：任意控件（QComboBox、QSpinBox 等）
- 整行不可点击（除非传入 `on_click` 回调）

### ToggleRow（BaseRow）

用于 Animation 等开关设置。

```
┌────────────────────────────────────────┐
│ [icon]  Label               ●  On       │
└────────────────────────────────────────┘
```

- 右侧：6px 圆形 QLabel（`border-radius: 3px`）
  - On：`background-color: accent_green`
  - Off：`background-color: text_muted`
- 状态文字 "On" / "Off"：11px，`text_muted`
- 整行可点击，切换状态时发射 `toggled(bool)` 信号

### MenuDivider（QWidget）

- 高度 1px
- 背景 `divider`
- 上下 margin 4px

### StyledButton（QPushButton）

统一按钮，支持四种变体：

| 变体 | 背景 | 文字 | hover |
|------|------|------|-------|
| primary | `accent_blue` | `text_inverse` | 亮度+10% |
| secondary | `surface_control` | `text_primary` | `surface_control_hover` |
| ghost | transparent | `text_secondary` | `surface_card_hover` |
| danger | `accent_red` | `#ffffff` | 亮度+10% |

- 统一 `border-radius: 8px`
- 统一 padding：`8px 14px`
- 支持 `setVariant(variant: str)` 动态切换

### IconLabel（QLabel）

- 固定宽度 16px，文字居中
- 12px 字体
- 颜色通过 theme 传入

---

## SettingsDrawer 重写

完全去掉传统对话框风格，改为 Vibe-Island NotchMenuView 风格。

### 布局

```
VStack(spacing: 4, margins: 8)
├── MenuRow(icon="←", label="Back")          ← 关闭抽屉
├── MenuDivider
├── MenuRow(label="Theme", ctrl=QComboBox)
├── MenuDivider
├── ToggleRow(icon="✦", label="Animation")
├── MenuDivider
├── MenuRow(label="Compact timeout", ctrl=QSpinBox)
├── MenuDivider
├── MenuRow(label="Position X", ctrl=QSpinBox)
├── MenuDivider
├── MenuRow(label="Position Y", ctrl=QSpinBox)
├── MenuDivider
├── MenuRow(label="Reset defaults")          ← 点击重置
└── Stretch
```

### 改动点

- 删除 `_title` QLabel 和 `_close_btn` QPushButton
- 删除 `_separator()` 方法，改用 `MenuDivider`
- 删除 `_row()` 方法，改用 `MenuRow` / `ToggleRow`
- 控件样式通过 `refresh_theme` 统一注入，不再用巨型 f-string stylesheet
- 背景继续使用 `surface_panel`，`border-radius: 16px`

---

## CompactPill 重构

消除所有硬编码色值。

- pending indicator：使用 `accent_amber` 替代 `#FF9800`
- count_label：使用 `text_primary` + 13px medium
- agents_label：使用 `text_secondary` + 11px
- settings_btn：ghost 风格，`text_secondary` → hover `text_primary`
- 背景/边框：使用 `surface_panel` / `border`

---

## ExpandedPanel 重构

消除所有硬编码色值。

- 面板背景：`surface_panel`
- 边框：`border`
- scroll viewport：`surface_panel`
- back_btn：ghost 风格
- detail_title：14px medium，`text_primary`

---

## Cards 重构

### BaseCard

- 背景：`surface_card`
- 圆角：`border-radius: 14px`
- title_label：11px，`text_secondary`
- body_label：13px，`text_primary`
- `refresh_theme` 不再是空实现，真正更新颜色

### PermissionCard

- dot：`accent_amber`
- title：13px semibold，`text_primary`
- badge：背景 `accent_amber` + 15% 透明度，文字 `accent_amber`
- tool_label：12px monospace，`accent_amber`
- input_label：11px，`text_muted`
- 按钮全部改用 `StyledButton`
  - Open Chat → ghost
  - Deny → secondary
  - Allow → primary（但背景用 `text_primary`，文字 `surface`，保持现有对比度）

### QuestionCard

- 选项按钮 → `StyledButton`（secondary 变体，左对齐）
- 输入框 → `surface_control` 背景，`border` 边框，`border-radius: 8px`
- Submit → `StyledButton`（primary）

### SessionListItem

- 背景：`surface_card`（`rgba(255,255,255,0.03)` 接近）
- hover：`surface_card_hover`
- dot：根据状态使用 `accent_green` / `accent_amber` / `text_muted`
- name：14px medium，`text_primary`
- desc：11px，`text_secondary`
- tags：背景 `rgba(255,255,255,0.08)`，文字 `text_secondary`，`border-radius: 4px`

---

## 交互优化

### 自动收起逻辑

```python
# island_window.py
_LEAVE_DELAY_MS = 800  # 从 400ms 改为 800ms
```

增加容错：鼠标在面板和胶囊之间快速移动时不会误收起。

### 动画统一

所有展开/收起动画统一使用：
- 时长：250ms（抽屉展开）、200ms（抽屉收起）、180ms（面板）
- 缓动：`QEasingCurve.Type.OutCubic`

### 主题切换即时响应

`Config.config_changed` 信号触发后，`IslandWindow._apply_theme()` 立即刷新所有子组件，无需重启。

---

## 迁移策略

按文件逐个替换，每改完一个文件运行一次 mock 模式验证：

1. `theme.py` — 扩展 token 体系
2. `components/` — 新增基础组件包
3. `settings_drawer.py` — 重写
4. `compact_pill.py` — 消除硬编码
5. `expanded_panel.py` — 消除硬编码
6. `cards/base_card.py` — 完善 refresh_theme
7. `cards/permission_card.py` — 使用 StyledButton
8. `cards/question_card.py` — 使用 StyledButton
9. `cards/session_list_item.py` — 消除硬编码
10. `island_window.py` — 调整延迟、统一动画

---

## 测试策略

- `tests/test_theme.py` — 验证 token 完整性、各预设值非空
- `tests/test_components.py` — 验证 BaseRow hover 状态切换、StyledButton 变体切换
- `tests/test_settings_drawer.py` — 保留现有信号/配置绑定测试，更新控件引用
- 手动验证：mock 模式下检查所有状态（compact、expanded、drawer open、theme switch）
