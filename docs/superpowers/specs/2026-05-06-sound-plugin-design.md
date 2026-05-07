# AI Island 音效插件设计文档

## 1. 概述

为 AI Island 增加音效提醒功能。当关键事件发生时，播放对应的音效文件，提升用户感知度。

## 2. 目标

- 新消息到达、权限请求、会话结束时播放对应音效
- 支持全局音量调节与静音开关
- 运行时热更新配置，无需重启
- 不影响核心功能稳定性（播放失败静默降级）

## 3. 架构设计

采用**插件化方案**（方案A），充分利用现有 `IslandPlugin` 架构：

```
EventSource → IslandWindow._on_event() → SoundPlugin.on_event()
                                      ↓
                              检查事件类型 + 防抖冷却
                                      ↓
                              QSoundEffect.play()
```

## 4. 组件说明

### 4.1 SoundPlugin

- **位置**：`island_ui/plugins/sound_plugin.py`
- **基类**：`IslandPlugin`
- **职责**：
  - `on_load()`：预加载三个 `QSoundEffect` 实例，读取初始配置
  - `on_event()`：接收事件，根据类型触发对应音效
  - 连接 `ConfigManager.config_changed` 信号，响应配置变更

### 4.2 音效文件

| 文件 | 用途 | 触发事件 |
|------|------|----------|
| `music/begin.mp3` | 提示新动态 | `chat.message` |
| `music/alarm.mp3` | 告警/需关注 | `permission.requested` |
| `music/end.mp3` | 结束/完成 | `session.ended` |

## 5. 事件映射与防抖

- `chat.message` → `begin.mp3`
- `permission.requested` → `alarm.mp3`
- `session.ended` → `end.mp3`

**防噪设计**：同类型音效 500ms 内不重复播放，避免消息刷屏时连续响铃。

## 6. 配置项

接入 `ConfigManager`，YAML 配置：

```yaml
sound:
  enabled: true   # 总开关，默认开启
  volume: 80      # 全局音量 0-100，默认 80
```

- `SoundPlugin` 在 `on_load()` 时读取初始配置
- 监听 `config_changed(key, value)` 信号，实时更新 `enabled` 和 `volume`

## 7. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 音效文件缺失或损坏 | `QSoundEffect.statusChanged` 检测 `Error` 状态，打印 warning，不影响主流程 |
| 播放异常 | try/except 包裹，静默失败 |
| `QtMultimedia` 不可用 | `on_load()` 捕获导入/初始化异常，插件优雅降级为空实现 |

## 8. 测试策略

- **单元测试** `tests/test_sound_plugin.py`：Mock `QSoundEffect`，验证事件类型映射、防抖逻辑、配置响应
- **Mock 模式自测**：`python island_ui/main.py --source mock`，观察事件触发时是否正确播放

## 9. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `island_ui/plugins/sound_plugin.py` | 音效插件主实现 |
| 新增 | `island_ui/plugins/__init__.py` | 插件包初始化 |
| 新增 | `tests/test_sound_plugin.py` | 单元测试 |
| 修改 | `island_ui/plugin_loader.py` | 加载 SoundPlugin（或扫描目录） |
| 修改 | `config/default.yaml` | 增加 `sound` 配置段默认值 |
