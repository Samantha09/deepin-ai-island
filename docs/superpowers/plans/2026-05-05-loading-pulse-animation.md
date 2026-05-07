# Loading 脉冲动画实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 running 状态的圆点上添加脉冲光环 CSS 动画。

**Architecture:** 纯前端 CSS 实现，在 `island.html` 的 `<style>` 区块添加 `@keyframes` 和两个类名的 `animation` 绑定，不改动 HTML 结构和 JS/Python 逻辑。

**Tech Stack:** CSS `@keyframes`, `box-shadow`, QWebEngine 渲染。

---

### Task 1: 添加脉冲光环 CSS 动画

**Files:**
- Modify: `island_ui/web/island.html:78-82`（`.status-dot` 规则下方）
- Modify: `island_ui/web/island.html:275-278`（`.session-status-dot.running` 规则）

- [ ] **Step 1: 添加 `@keyframes pulse-ring`**

在 `.status-dot.error` 规则（第 82 行）之后、`<!-- 中间信息 -->` 注释之前，插入以下 CSS：

```css
    @keyframes pulse-ring {
      0% {
        box-shadow: 0 0 0 0 rgba(102, 232, 248, 0.6);
      }
      70% {
        box-shadow: 0 0 0 6px rgba(102, 232, 248, 0);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(102, 232, 248, 0);
      }
    }
    .status-dot.active {
      animation: pulse-ring 1.5s ease-out infinite;
    }
```

- [ ] **Step 2: 给会话卡片圆点绑定动画**

将 `.session-status-dot.running` 规则从：

```css
    .session-status-dot.running { background: #66E8F8; }
```

修改为：

```css
    .session-status-dot.running {
      background: #66E8F8;
      animation: pulse-ring 1.5s ease-out infinite;
    }
```

- [ ] **Step 3: 启动 mock 模式验证动画效果**

Run:
```bash
source .venv/bin/activate && python island_ui/main.py --source mock
```

验证 checklist：
- [ ] mock 剧本发射 running 状态事件后，顶部胶囊青色圆点有扩散脉冲效果
- [ ] 悬停展开会话面板，running 状态的会话卡片青色圆点有同步脉冲效果
- [ ] 非 running 状态（idle/completed/needs_attention）的圆点保持静态，无脉冲
- [ ] 动画流畅，无明显性能问题

- [ ] **Step 4: 提交**

```bash
git add island_ui/web/island.html
git commit -m "$(cat <<'EOF'
feat(ui): running 状态圆点增加脉冲光环动画

在顶部胶囊状态点和会话卡片状态点上，为 running/active
状态添加 CSS box-shadow 脉冲扩散动画，提升活跃感知。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```
