---
name: repo-init
version: 1.1.0
description: >
  新项目强制脚手架：创建 GitHub 仓库或对已有仓库补全必备文件。
  CLAUDE.md 和 PLAN.md 是强制要求，缺少则阻断后续步骤。
  触发词：新建项目、初始化仓库、scaffold、repo init、项目脚手架、
          create repo, new project, init project, setup repo
metadata:
  requires:
    bins: ["gh", "git"]
---

# repo-init — 新项目强制脚手架

**Announce at start:** "I'm using the repo-init skill to set up the project structure."

## BLOCKING REQUIREMENT

```
CLAUDE.md 和 PLAN.md 是强制文件。
缺少任意一个 → 立刻生成，不可跳过，不可延后。
没有这两个文件，+new 和 +scaffold 流程不得继续。
```

---

## 文件分级

| 级别 | 文件 | 缺失时 | 作用 |
|------|------|--------|------|
| ⭐ **强制** | `CLAUDE.md` | **阻断，立刻生成** | 项目架构 + 开发规范 + 命令速查 + 排障指南，Claude 每次对话自动加载 |
| ⭐ **强制** | `PLAN.md` | **阻断，立刻生成** | ① 主线计划（阶段路线图）② 支线计划（并行调研/实验/优化方向） |
| 推荐 | `README.md` | 生成但不阻断 | 用户视角快速上手 |
| 推荐 | `.github/workflows/ci.yml` | 生成但不阻断 | CI 自动化 |
| 推荐 | `.github/ISSUE_TEMPLATE/` | 生成但不阻断 | issue 角色模板（对接 team-collab） |

### CLAUDE.md 应包含什么

参考 agora-v4/CLAUDE.md 的结构：项目定位、架构图、目录结构、子系统说明、关键命令、开发规范、排障指南。**每行都应该是不写就会踩坑的信息，不写废话。**

### PLAN.md 应包含什么

- **主线**：当前阶段、路线图（Stage 列表 + 状态）、当前 Stage 的任务拆解和验收标准
- **支线**：并行进行的调研/实验/优化方向，每条一句话说明价值和状态

---

## Shortcuts

| Shortcut | 动作 | 场景 |
|----------|------|------|
| `+new` | 创建新 GitHub 仓库 + 强制生成全部文件 | 从零开始 |
| `+scaffold` | 对**已有仓库**检测并补全缺失文件（强制文件优先） | 存量项目补齐 |
| `+check` | 仅检查，列出缺失项，不写文件 | 快速诊断 |

---

## 决策矩阵

| 用户说 | 执行 |
|--------|------|
| 「新建项目 xxx」「create repo xxx」 | `+new` |
| 「帮我初始化这个仓库」「这个项目缺什么」 | `+scaffold` |
| 「检查下项目结构」「缺哪些文件」 | `+check` |

---

## 与 team-collab 的关系

```
repo-init    ──一次性──▶  CLAUDE.md（强制）+ PLAN.md（强制）+ 其他推荐文件
                                │
team-collab  ──日常循环──▶  issue → branch → PR → +merge（含文档同步）
```

`+new` / `+scaffold` 完成后，在 `CLAUDE.md` 的开发规范章节自动写入：

> 本项目使用 team-collab skill 管理开发流程。  
> 小修走 `+quick`，功能/Bug 走 `+issue` → `+branch` → `+pr` → `+merge`。

---

## Red Flags

- 说「先不写 CLAUDE.md，等项目稳定了再写」→ STOP，现在写，哪怕只有 3 行
- 说「PLAN.md 不重要，我心里有数」→ STOP，Claude 没有你的心，它只看文件
- `+scaffold` 时发现 CLAUDE.md 存在但内容少于 10 行 → 提示用户补全

---

## 详细操作文档

- [`+new` 新建仓库全流程](references/ri-new.md)
- [`+scaffold` 存量项目补全](references/ri-scaffold.md)
- [CLAUDE.md 模板与填写指南](references/ri-claude-md.md)
- [README.md 模板](references/ri-readme.md)
- [PLAN.md 模板](references/ri-plan-md.md)
- [.github/ 配置（CI + issue templates）](references/ri-github-setup.md)
