# 会话列表关闭按钮与排序设计

## 背景

AI Island 主窗口的会话列表面板目前仅展示会话信息，用户无法手动清理已结束或不再关注的会话。本设计在会话卡片最右侧增加关闭按钮，并优化列表排序逻辑。

## 目标

1. 每个会话卡片支持手动关闭（从列表移除）
2. 关闭按钮美观、不干扰默认视觉
3. 会话列表按状态优先级 + 最后更新时间排序

## 设计细节

### 一、关闭按钮

#### 前端展示（island.html）

- **位置**：`session-card-row` 最右侧，与左侧状态点和名称同行
- **图标**：使用内联 SVG（基于 `icons/delete.svg` 路径），尺寸 16×16px
- **显隐策略**：默认 `opacity: 0`；整个 `.session-card` hover 时，`opacity: 1`，过渡 140ms ease
- **颜色**：默认 `rgba(255, 255, 255, 0.4)`；按钮自身 hover 时变为 `#EF4444`（红色危险提示）
- **点击行为**：`e.stopPropagation()` 阻止冒泡，调用 `bridge.closeSession(session.id)`

#### Python 交互（island_window.py）

- `IslandBridge` 新增槽函数：
  ```python
  @Slot(str)
  def closeSession(self, session_id: str) -> None:
      self.window.close_session(session_id)
  ```
- `IslandWindow` 新增方法：
  ```python
  def close_session(self, session_id: str) -> None:
      self._sessions.pop(session_id, None)
      self._push_sessions_to_web()
  ```
- **后续行为**：关闭仅从 `self._sessions` 移除；若该会话后续有新事件，会重新创建并出现在列表中

### 二、会话排序

#### Session 模型变更（session.py）

- 新增字段：`last_updated: float = field(default_factory=lambda: datetime.now().timestamp())`
- `add_event()` 方法末尾追加：`self.last_updated = event.timestamp`

#### 推送逻辑变更（island_window.py）

- 保持现有分组顺序：`needs_attention` → `running` → `其他`
- 每组内部按 `last_updated` **降序**排列（最新更新在前）

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `island_ui/web/island.html` | 修改 | 增加关闭按钮 SVG、CSS、JS 事件 |
| `island_ui/island_window.py` | 修改 | 增加 `closeSession` 桥接槽和 `close_session` 方法 |
| `island_ui/session.py` | 修改 | 增加 `last_updated` 字段，在 `add_event` 中更新 |

## 测试要点

1. Mock 模式启动后，悬停会话面板，卡片右侧出现垃圾桶图标
2. 点击图标后，该会话从列表消失
3. 重新注入该 session 的事件，会话重新出现在列表
4. 多个会话时，`needs_attention` 组在前，同组内最后更新的在前
