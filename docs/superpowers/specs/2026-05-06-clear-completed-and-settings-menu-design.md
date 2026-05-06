# 一键清除已完成会话 + 设置菜单改造 Design

## 目标

在主面板增加一个"清除已完成"按钮，并将设置按钮从"打开详情页"改造为"设置下拉菜单"，集成音效控制、关于、退出等功能。

## 架构

前端（island.html）通过 HTML/CSS 实现下拉菜单，通过 QWebChannel 与后端（island_window.py）通信。后端操作 `ConfigManager` 和 `_sessions` 状态。

## 组件

### 1. 清除已完成按钮

- **位置**：主面板顶部 `#status-row` 的 `.status-right` 内，settings-btn 旁边
- **图标**：垃圾桶 SVG（`trash-icon`）
- **行为**：点击后调用 `bridge.clearCompletedSessions()`
- **清除范围**：所有 `status == "completed"` 或 `status == "idle"` 的会话
- **确认对话框**：无，直接清除

### 2. 设置下拉菜单

- **触发**：点击 settings-btn（⋯）
- **关闭**：再次点击 settings-btn，或点击菜单外部区域
- **菜单项**：
  - **音效开关**：checkbox，绑定 `sound.enabled`，调用 `bridge.setSoundEnabled(bool)`
  - **音量滑块**：range input 0-100，绑定 `sound.volume`，调用 `bridge.setSoundVolume(int)`
  - **分隔线**
  - **关于**：显示应用名称和版本（静态文本或简单弹窗）
  - **退出**：调用 `bridge.quitApp()`

### 3. 后端通信接口（QWebChannel）

新增暴露给前端的方法：

```python
def clear_completed_sessions(self) -> None
def set_sound_enabled(self, enabled: bool) -> None
def set_sound_volume(self, volume: int) -> None
def quit_app(self) -> None
```

### 4. 配置热更新

`set_sound_enabled` / `set_sound_volume` 直接修改 `ConfigManager`，触发 `config_changed` 信号，SoundPlugin 自动响应。

## 数据流

```
用户点击清除按钮
  → 前端: bridge.clearCompletedSessions()
  → 后端: IslandWindow.clear_completed_sessions()
  → 后端: 遍历 _sessions，移除 completed/idle
  → 后端: _push_sessions_to_web()
  → 前端: 更新 session-list

用户点击设置开关
  → 前端: bridge.setSoundEnabled(true/false)
  → 后端: ConfigManager.set("sound.enabled", value)
  → 后端: config_changed 信号
  → SoundPlugin: 自动更新
```

## 错误处理

- 清除时没有已完成会话：静默忽略，无操作
- 配置保存失败：由 ConfigManager 处理，前端不感知

## 测试

- 单元测试：验证 `clear_completed_sessions` 正确移除指定状态会话，保留 running/needs_attention
- Mock 模式验证：创建 completed/idle/running 会话，点击清除按钮，观察列表更新
