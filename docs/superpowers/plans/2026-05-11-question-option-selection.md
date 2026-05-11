# Claude Code 选项选择支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI Island 的悬停展开区域新增交互式 Question Card，支持选项选择和自定义输入回复。

**Architecture:** 复用现有的权限审批事件流模式。Hook 层拦截提问事件 → Socket 发送到 AI Island → expanded.html 渲染 Question Card → 用户选择/输入 → Bridge 回传 → Socket 返回 Hook → Claude Code。前端用蓝色调区分 Question Card 与橙色权限卡片。

**Tech Stack:** PySide6 (Qt6), Python 3.12, QWebEngineView (HTML/CSS/JS), Unix Socket, YAML

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `island_ui/events.py` | QuestionAsked 类无需改动，已含 options 字段 |
| `island_ui/session.py` | `add_event` 已处理 `question.asked` 状态变更，无需改动 |
| `island_ui/claude_code_source.py` | 新增 `question.asked` 事件解析 + `respond_to_question` 方法 |
| `island_ui/island_window.py` | 新增 Bridge Slot、前端渲染推送、respond_question 逻辑 |
| `island_ui/web/expanded.html` | 新增 Question Card CSS + JS（addQuestionCard, respondQuestion） |
| `claude_hooks/ai_island_hook.py` | 新增提问事件拦截、超时等待回复、包装响应格式 |
| `island_ui/event_source.py` | MockEventSource 已含 QuestionAsked，微调 payload 添加 tool_use_id |
| `tests/test_events.py` | 无需改动，QuestionAsked 测试已存在 |
| `tests/test_session.py` | 新增 question.asked 状态变更测试 |

---

## Task 1: Socket Server 层 — 新增提问事件解析与回复通道

**Files:**
- Modify: `island_ui/claude_code_source.py:184-218` (SocketServerThread._handle_client)
- Modify: `island_ui/claude_code_source.py:255-256` (ClaudeCodeEventSource)
- Modify: `island_ui/claude_code_source.py:505-605` (_parse_socket_event)

**Context:** 当前 `SocketServerThread` 在 `_handle_client` 中只有 `PermissionRequest` 会等待响应（client socket 不关闭，存入 `_pending`）。其他事件直接关闭 socket。Question 事件需要同样的双向通道。

- [ ] **Step 1: 新增 SocketServerThread 提问回复方法**

在 `respond_to_permission` 方法下方，新增 `respond_to_question`：

```python
def respond_to_question(self, tool_use_id: str, answer: str) -> bool:
    """向等待中的 question.asked 客户端发送用户答案。"""
    with self._lock:
        pending = self._pending.get(tool_use_id)
        if pending is None:
            return False
        client_sock, event_obj, _ = pending

    response = {"answer": answer}
    try:
        data = json.dumps(response, ensure_ascii=False).encode("utf-8")
        client_sock.sendall(data)
        client_sock.close()
    except OSError:
        pass
    finally:
        event_obj.set()
        with self._lock:
            self._pending.pop(tool_use_id, None)
    return True
```

- [ ] **Step 2: 在 _handle_client 中新增 question 事件的双向等待逻辑**

在 `_handle_client` 的 `PermissionRequest` 处理分支之后（约 line 211），`Non-permission events` 处理之前（约 line 213），插入：

```python
        if event_name in ("QuestionAsked", "question.asked"):
            resolved_tool_use_id = tool_use_id
            if not resolved_tool_use_id:
                resolved_tool_use_id = self._pop_cached_tool_use_id(session_id, tool_name, tool_input)

            if resolved_tool_use_id:
                data["tool_use_id"] = resolved_tool_use_id
                event_obj = threading.Event()
                with self._lock:
                    self._pending[resolved_tool_use_id] = (client, event_obj, time.time())
                self.event_received.emit(data)
                event_obj.wait(timeout=86400)
                with self._lock:
                    if resolved_tool_use_id in self._pending:
                        try:
                            client.sendall(json.dumps({"answer": ""}).encode("utf-8"))
                            client.close()
                        except OSError:
                            pass
                        self._pending.pop(resolved_tool_use_id, None)
                return
            else:
                client.close()
                self.event_received.emit(data)
                return
```

- [ ] **Step 3: 在 ClaudeCodeEventSource 暴露 respond_to_question**

在 `respond_to_permission` 方法下方：

```python
def respond_to_question(self, tool_use_id: str, answer: str) -> bool:
    return self._server.respond_to_question(tool_use_id, answer)
```

- [ ] **Step 4: 在 _parse_socket_event 中新增 question.asked 解析**

在 `_parse_socket_event` 方法中，在 `PermissionRequest` 处理之后（约 line 553），`PreToolUse` 之前（约 line 555），插入：

```python
        if event_name in ("QuestionAsked", "question.asked"):
            question = payload.get("question", "")
            options = payload.get("options")
            return QuestionAsked(
                session_id=session_id,
                question=question,
                options=options,
                payload={"tool_use_id": payload.get("tool_use_id", ""), **payload},
                timestamp=timestamp,
            )
```

- [ ] **Step 5: Commit**

```bash
git add island_ui/claude_code_source.py
git commit -m "feat(10565): Socket Server 层新增提问事件解析与回复通道"
```

---

## Task 2: Hook 层 — 新增提问事件拦截与响应

**Files:**
- Modify: `claude_hooks/ai_island_hook.py:152-202` (send_event_and_wait)
- Modify: `claude_hooks/ai_island_hook.py:229-253` (main response wrapping)

**Context:** 当前 hook 只处理 `PermissionRequest` 事件的等待响应。需要新增对 `QuestionAsked` 的同等处理，并支持两种响应格式回传。

- [ ] **Step 1: 扩展 send_event_and_wait 支持 QuestionAsked 等待**

修改 `send_event_and_wait` 中的事件判断逻辑（约 line 176）：

```python
    event_name = data.get("event") or data.get("hook_event_name", "")
    if event_name in ("PermissionRequest", "QuestionAsked", "question.asked"):
        sock.settimeout(PERMISSION_TIMEOUT)
        try:
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    resp = json.loads(b"".join(chunks).decode("utf-8"))
                    return resp
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        except socket.timeout:
            if event_name == "PermissionRequest":
                return {"decision": "deny", "reason": "timeout"}
            else:
                return {"answer": ""}
        except OSError:
            if event_name == "PermissionRequest":
                return {"decision": "deny", "reason": "connection lost"}
            else:
                return {"answer": ""}
```

- [ ] **Step 2: 扩展 main 函数中的响应包装**

在 `main()` 函数的响应包装逻辑中（约 line 230），在 PermissionRequest 包装之后，添加 QuestionAsked 包装：

```python
        # PermissionRequest 响应包装
        decision = response.get("decision", "")
        if decision:
            if not decision:
                decision = "allow" if response.get("approved") else "deny"
            wrapped = {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {
                        "behavior": decision
                    }
                }
            }
            if decision == "deny":
                reason = response.get("reason", "")
                if reason:
                    wrapped["hookSpecificOutput"]["decision"]["message"] = reason
                else:
                    wrapped["hookSpecificOutput"]["decision"]["message"] = "Denied by user via AI Island"
            print(json.dumps(wrapped), file=sys.stdout)
            sys.stdout.flush()
            return

        # QuestionAsked 响应包装
        answer = response.get("answer", "")
        if answer or "answer" in response:
            wrapped = {
                "hookSpecificOutput": {
                    "hookEventName": "QuestionAsked",
                    "answer": answer
                }
            }
            print(json.dumps(wrapped), file=sys.stdout)
            sys.stdout.flush()
```

**注意：** 需要重构原 `decision` 变量的空值检查逻辑，原代码在 line 234-235 有一个 `if not decision` 的冗余检查，新代码中将其删除。

- [ ] **Step 3: Commit**

```bash
git add claude_hooks/ai_island_hook.py
git commit -m "feat(10565): Hook 层新增提问事件拦截与响应包装"
```

---

## Task 3: island_window.py — 新增问题回复桥接与处理

**Files:**
- Modify: `island_ui/island_window.py:22-80` (IslandBridge)
- Modify: `island_ui/island_window.py:82-105` (ExpandedBridge)
- Modify: `island_ui/island_window.py:836-870` (_on_event question handling)
- Modify: `island_ui/island_window.py:999-1041` (respond_permission 附近)

- [ ] **Step 1: IslandBridge 新增 respondQuestion Slot**

在 `IslandBridge` 的 `allowAllPermission` 方法之后（约 line 47），插入：

```python
    @Slot(str, str)
    def respondQuestion(self, session_id: str, answer: str) -> None:
        self.window.respond_question(session_id, answer)
```

- [ ] **Step 2: ExpandedBridge 新增 respondQuestion Slot**

在 `ExpandedBridge` 的 `allowAllPermission` 方法之后（约 line 103），插入：

```python
    @Slot(str, str)
    def respondQuestion(self, session_id: str, answer: str) -> None:
        self.window.main_window.respond_question(session_id, answer)
```

- [ ] **Step 3: 在 _on_event 中处理 question.asked 事件**

在 `_on_event` 方法中，在 `permission.requested` 处理分支之后（约 line 870），添加 `question.asked` 的处理：

```python
        # 提问事件：自动触发悬停展开效果
        if event.type == "question.asked":
            self._auto_expand_for_permission()
```

- [ ] **Step 4: 新增 respond_question 方法**

在 `respond_permission_all` 方法之后（约 line 1041），插入：

```python
    def respond_question(self, session_id: str, answer: str) -> None:
        """处理用户从 Question Card 提交的答案。"""
        self._permission_auto_close_timer.stop()
        session = self._sessions.get(session_id)
        if not session:
            return
        # 找到最近的未解决 question 事件
        for event in reversed(session.events):
            if event.type == "question.asked":
                tid = event.payload.get("tool_use_id", "")
                if tid and hasattr(self._event_source, "respond_to_question"):
                    self._event_source.respond_to_question(tid, answer)
                session.mark_permission_resolved(tid)
                session.add_event(ChatMessage(session_id=session.id, role="user", content=answer))
                self._push_sessions_to_web()
                break
        if self.expanded_window.isVisible():
            self.expanded_window.close_to_main()
```

- [ ] **Step 5: Commit**

```bash
git add island_ui/island_window.py
git commit -m "feat(10565): 主窗口新增问题回复桥接与处理逻辑"
```

---

## Task 4: expanded.html — 新增 Question Card 前端交互

**Files:**
- Modify: `island_ui/web/expanded.html:182-245` (CSS 区域)
- Modify: `island_ui/web/expanded.html:418-441` (renderEvent)
- Modify: `island_ui/web/expanded.html:513-518` (respond 函数之后)

- [ ] **Step 1: 新增 Question Card CSS**

在 `.permission-card` 样式之前（约 line 182），插入 Question Card 样式：

```css
    /* 提问卡片 */
    .question-card {
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 10px;
    }
    .question-title {
      font-size: 12px;
      font-weight: 600;
      color: #3B82F6;
      margin-bottom: 8px;
    }
    .question-options {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .question-option-btn {
      padding: 8px 12px;
      border: none;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 140ms ease;
      background: rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.9);
      text-align: left;
    }
    .question-option-btn:hover {
      background: rgba(59, 130, 246, 0.35);
      color: #fff;
    }
    .question-other-btn {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .question-other-btn .edit-icon {
      font-size: 13px;
      opacity: 0.6;
    }
    .question-input-area {
      display: none;
      margin-top: 6px;
      gap: 6px;
    }
    .question-input-area.expanded {
      display: flex;
    }
    .question-input {
      flex: 1;
      padding: 8px 10px;
      border: 1px solid rgba(59, 130, 246, 0.4);
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.25);
      color: rgba(255, 255, 255, 0.9);
      font-size: 12px;
      outline: none;
    }
    .question-input::placeholder {
      color: rgba(255, 255, 255, 0.35);
    }
    .question-send-btn {
      padding: 8px 14px;
      border: none;
      border-radius: 8px;
      background: rgba(59, 130, 246, 0.85);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 140ms ease;
    }
    .question-send-btn:hover {
      background: rgba(59, 130, 246, 1);
    }
    .question-card.answered {
      opacity: 0.5;
      pointer-events: none;
    }
    .question-answer-result {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.6);
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid rgba(59, 130, 246, 0.15);
    }
```

- [ ] **Step 2: 修改 renderEvent 中 question.asked 的处理**

将 `renderEvent` 中 `question.asked` 的分支（约 line 432-434）：

```javascript
      } else if (type === "question.asked") {
        const question = payload.question || "";
        const options = payload.options || [];
        const toolUseId = payload.tool_use_id || "";
        if (!resolvedPermissions.has(toolUseId)) {
          addQuestionCard(toolUseId, question, options);
        }
```

- [ ] **Step 3: 新增 addQuestionCard 和 respondQuestion 函数**

在 `respond` 函数之后（约 line 518），插入：

```javascript
    function addQuestionCard(toolUseId, question, options) {
      const card = document.createElement("div");
      card.className = "question-card";
      card.dataset.toolUseId = toolUseId;

      const title = document.createElement("div");
      title.className = "question-title";
      title.textContent = "❓ " + (question || "请选择一个选项");

      const optionsContainer = document.createElement("div");
      optionsContainer.className = "question-options";

      // 渲染选项按钮
      (options || []).forEach(function (opt) {
        const btn = document.createElement("button");
        btn.className = "question-option-btn";
        btn.textContent = opt;
        btn.addEventListener("click", function () {
          respondQuestion(toolUseId, opt);
          card.classList.add("answered");
          const result = document.createElement("div");
          result.className = "question-answer-result";
          result.textContent = "已选择: " + opt;
          card.appendChild(result);
        });
        optionsContainer.appendChild(btn);
      });

      // "其他..." 按钮 + 输入框
      const otherBtn = document.createElement("button");
      otherBtn.className = "question-option-btn question-other-btn";
      otherBtn.innerHTML = '<span>其他...</span><span class="edit-icon">✎</span>';

      const inputArea = document.createElement("div");
      inputArea.className = "question-input-area";

      const input = document.createElement("input");
      input.className = "question-input";
      input.type = "text";
      input.placeholder = "请输入你的回答...";

      const sendBtn = document.createElement("button");
      sendBtn.className = "question-send-btn";
      sendBtn.textContent = "发送";

      inputArea.appendChild(input);
      inputArea.appendChild(sendBtn);

      otherBtn.addEventListener("click", function () {
        inputArea.classList.toggle("expanded");
        if (inputArea.classList.contains("expanded")) {
          input.focus();
        }
      });

      function submitCustomAnswer() {
        const val = input.value.trim();
        if (!val) return;
        respondQuestion(toolUseId, val);
        card.classList.add("answered");
        const result = document.createElement("div");
        result.className = "question-answer-result";
        result.textContent = "已输入: " + val;
        card.appendChild(result);
      }

      sendBtn.addEventListener("click", submitCustomAnswer);
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") submitCustomAnswer();
      });

      optionsContainer.appendChild(otherBtn);
      optionsContainer.appendChild(inputArea);

      card.appendChild(title);
      card.appendChild(optionsContainer);

      content.appendChild(card);
    }

    function respondQuestion(toolUseId, answer) {
      resolvedPermissions.add(toolUseId);
      if (bridge) {
        bridge.respondQuestion(currentSessionId, answer);
      }
    }
```

- [ ] **Step 4: Commit**

```bash
git add island_ui/web/expanded.html
git commit -m "feat(10565): 展开区域新增 Question Card 交互 UI"
```

---

## Task 5: Mock 测试支持 — 微调 MockEventSource 的 QuestionAsked payload

**Files:**
- Modify: `island_ui/event_source.py:63` (MockEventSource QuestionAsked)

- [ ] **Step 1: 给 MockEventSource 的 QuestionAsked 添加 tool_use_id**

修改 `MockEventSource._build_timeline` 中 session s2 的 QuestionAsked（约 line 63）：

```python
            (5.0, QuestionAsked(
                session_id=s2,
                question="Which deployment target?",
                options=["Production", "Staging", "Local only"],
                payload={"tool_use_id": "mock-question-001"},
            )),
```

- [ ] **Step 2: Commit**

```bash
git add island_ui/event_source.py
git commit -m "chore(10565): Mock 事件源补充提问事件的 tool_use_id"
```

---

## Task 6: 测试 — 新增 Session 对 question.asked 状态变更的测试

**Files:**
- Modify: `tests/test_session.py`

- [ ] **Step 1: 新增 question.asked 状态变更测试**

在 `test_session.py` 末尾添加：

```python
def test_question_asked_sets_needs_attention():
    from island_ui.events import QuestionAsked, ChatMessage
    s = Session(id="test", name="test", agent="Claude Code", terminal="")
    s.status = "running"
    s.add_event(QuestionAsked(session_id="test", question="Continue?", options=["Yes", "No"]))
    assert s.status == "needs_attention"


def test_question_answered_restores_running():
    from island_ui.events import QuestionAsked, ChatMessage, QuestionAnswered
    s = Session(id="test", name="test", agent="Claude Code", terminal="")
    s.status = "running"
    s.add_event(QuestionAsked(session_id="test", question="Continue?", options=["Yes", "No"]))
    assert s.status == "needs_attention"
    # 模拟用户回答后，添加一个 chat.message 或 progress.updated 来恢复状态
    s.add_event(ChatMessage(session_id="test", role="user", content="Yes"))
    assert s.status == "running"
```

- [ ] **Step 2: 运行测试**

```bash
source .venv/bin/activate
pytest tests/test_session.py -v
```

预期输出：`test_question_asked_sets_needs_attention PASSED`、`test_question_answered_restores_running PASSED`

- [ ] **Step 3: Commit**

```bash
git add tests/test_session.py
git commit -m "test(10565): 新增 question.asked 状态变更测试"
```

---

## Task 7: 集成自测

**Files:** 不涉及文件修改，纯验证

- [ ] **Step 1: Mock 模式验证 Question Card UI**

```bash
source .venv/bin/activate
python island_ui/main.py --source mock
```

验证 checklist：
- [ ] 悬停会话 s2-codex 展开后能看到蓝色 Question Card
- [ ] 显示 "Which deployment target?" + 三个选项 + "其他..."
- [ ] 点击选项后卡片变为灰色已回答状态
- [ ] 点击"其他..."展开输入框，输入后发送回传
- [ ] 无 JS 报错

- [ ] **Step 2: Socket 手动注入验证**

```python
import json, socket, time

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/tmp/ai-island.sock")

sock.sendall(json.dumps({
    "event": "QuestionAsked",
    "session_id": "test-question-001",
    "tool_use_id": "tuq-001",
    "payload": {
        "question": "Select a framework",
        "options": ["React", "Vue", "Svelte"]
    }
}).encode())

# 等待回复（模拟用户选择）
resp = sock.recv(4096)
print("Got answer:", json.loads(resp.decode()))
sock.close()
```

验证 checklist：
- [ ] AI Island 显示新 Question Card
- [ ] 选择后 socket 收到 `{"answer": "React"}` 之类的回复

- [ ] **Step 3: Commit（如果测试通过）**

```bash
git commit --allow-empty -m "test(10565): 集成自测通过"
```

---

## Self-Review Checklist

| Spec 要求 | 实现任务 |
|-----------|----------|
| 新增提问事件拦截 | Task 2 (Hook 层) |
| `question.asked` 事件解析 | Task 1 (Socket Server 解析) |
| 交互式 Question Card | Task 4 (expanded.html) |
| 选项选择 + 自定义输入 | Task 4 (JS 交互逻辑) |
| 回复回传 Claude Code | Task 1 + Task 3 (respond_to_question 链路) |
| Mock 测试支持 | Task 5 |
| 蓝色视觉区分 | Task 4 (CSS `.question-card`) |
| 超时回退 | Task 2 (hook 层超时返回空字符串) |

**Placeholder scan:** 无 TBD/TODO，所有代码块完整。
**Type consistency:**
- `respond_to_question(tool_use_id: str, answer: str)` 在 Task 1 和 Task 3 中签名一致
- `respondQuestion(toolUseId, answer)` 在 Task 4 JS 中和 Task 3 Bridge Slot 中命名对应
- `question.asked` / `QuestionAsked` 事件名在各文件中一致
