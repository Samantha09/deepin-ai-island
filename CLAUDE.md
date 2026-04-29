# CLAUDE.md

Deepin AI Island — PySide6 (Qt6), Python 3.12+

## 关于本文件

`CLAUDE.md` 为 Claude Code 提供项目级指导。

## 开发工作流（Superpowers Skills）

本项目全流程使用 Superpowers skills 套件，所有开发任务必须遵循以下工作流：

| 场景 | Skill |
|------|-------|
| 任何创造性工作（新功能、新组件、修改行为） | `/superpowers:brainstorming` |
| 多步骤实现任务（有规格或需求文档） | `/superpowers:writing-plans` |
| 执行已有实现计划 | `/superpowers:executing-plans` |
| 功能开发或 Bug 修复 | `/superpowers:test-driven-development` |
| 遇到 Bug、测试失败、异常行为 | `/superpowers:systematic-debugging` |
| 即将声称工作完成/通过 | `/superpowers:verification-before-completion` |
| 完成实现，需要集成 | `/superpowers:finishing-a-development-branch` |
| 完成任务后请求审查 | `/superpowers:requesting-code-review` |
| 收到代码审查反馈 | `/superpowers:receiving-code-review` |
| 2+ 个独立任务可并行 | `/superpowers:dispatching-parallel-agents` |

关键规则：
- **开发前必须先阅读编码规范**（memory: `feedback-coding-standards.md`）
- **编码前必须先 brainstorming**
- **TDD 优先**：先写测试，再写实现
- **证据优先于断言**：声称完成前必须有验证命令的输出作为证据
- **收到审查反馈时保持严谨**：不盲目同意，技术上验证每条反馈

## 提交规范

遵循 Conventional Commits：

```
<类型>(<范围>): <描述>
```

**类型**：`feat` / `fix` / `hotfix` / `perf` / `build` / `ci` / `chore` / `docs` / `refactor` / `revert` / `style` / `test`

**范围（括号内容）**：
- `feat` / `fix`：括号内**必须是纯数字**（需求/缺陷 ID），如 `feat(10565): ...`
- 其他类型：括号内使用英文，如 `docs(doc): ...`、`refactor(core): ...`

**描述**：至少 5 个字符

**分支名规范**：`master` | `dev` | `feature` | `master_xxx` | `dev_xxx` | `feature_xxx` | `maintenance_xxx` | `bugfix`，只能使用英文字母、数字和下划线

注意：commit message 中**不要**添加 `Co-Authored-By` 行。

## 项目特定规范

- **技术栈**：PySide6 (Qt6)，Python 3.12+，YAML 配置，虚拟环境 `.venv/`
- **运行**：`source .venv/bin/activate && python island_ui/main.py`
- **注释语言**：代码注释、文档字符串（docstring）使用中文
- **Commit 语言**：Commit message 的描述部分使用中文（类型/范围仍遵循 Conventional Commits 英文规范）
- **架构细节**、**类说明**、**样式规范**、**Phase 2 Hook 架构**、**扩展指南**、**快捷键**见 memory: `project-overview.md`
- **已知问题与修复计划**见 memory: `ai_island_issues.md`

## Skills

| Skill | Purpose |
|-------|---------|
| `/dynamic-island-development` | 项目级 Skill，开发灵动岛相关功能前必须调用。涵盖刘海 UI、会话状态机、IPC/Hooks、主题、权限审批、UI 组件、插件架构、多终端集成。 |

## 参考文档

开发前按需阅读 memory 中的详细规范：

| 主题 | Memory 文件 |
|------|------------|
| **编码规范（必读）** | `feedback-coding-standards.md` — BLOCKER/WARNING/SUGGESTION 自检清单、常见陷阱、安全审查检查表 |
| **Python 编码规范** | `python-coding-standards.md` — 命名、格式、文档字符串、类型注解、并发编程、装饰器模式、测试实践 |
| **项目架构与技术细节** | `project-overview.md` — 目录结构、核心架构、类说明、样式规范、Phase 2、扩展指南、快捷键 |
| **已知问题** | `ai_island_issues.md` — bug 清单与修复计划 |
| **编译/部署** | `build-deploy.md` — 编译命令、部署流程、环境配置 |
| **测试环境** | `test-environment.md` — 登录方法、环境配置、端口、路径 |
| **文档索引** | `doc-index.md` — 需求文档、设计文档、接口文档目录 |
