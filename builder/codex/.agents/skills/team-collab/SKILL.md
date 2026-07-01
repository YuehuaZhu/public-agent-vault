---
name: team-collab
version: 1.1.0
description: >
  团队协同开发工作流：任何角色用自然语言创建 GitHub Issue → 分支 → PR → merge → 文档同步 → 发版。
  适用角色：产品经理、运营、商务、算法、工程师。
  触发词：创建issue、提需求、报bug、新功能、开分支、提PR、merge PR、CI红了、CI挂了、
          看进展、发版说明、更新文档、同步文档、
          create issue, new feature, bug report, open PR, merge PR, CI failed, release notes, hotfix
metadata:
  requires:
    bins: ["gh", "git"]
  cliHelp: "gh --help"
---

# team-collab — 团队协同开发工作流

**Announce at start:** "I'm using the team-collab skill to manage this workflow."

## The Iron Law

```
PR merge 后不同步 CLAUDE.md 和 PLAN.md = 文档欠债。
欠债累积 = 下一个接手的人（包括你自己）看到的是谎言。
使用 +merge 代替手动 gh pr merge，文档同步自动提醒。
```

---

## 两条轨道

```
有新想法/Bug/需求
       │
       ▼
  值得追踪？
  ├── 是（功能/重大Bug/研究）→ 轨道 A：+issue → +branch → 开发 → +pr → +merge
  └── 否（小修/顺手改）      → 轨道 B：+quick → 开发 → +pr → +merge
```

Issue 列表只留值得追踪的事，小改动追溯靠 PR + commit 历史。

**CI 是本地前置的**：`+pr` 在建 PR 前先本地跑 CI 当门禁（红了先修、不建 PR），合并以本地 CI 为准——不依赖 GitHub Actions（它常因 billing/额度跑不起来）。详见 [本地 CI](references/tc-local-ci.md)。

---

## Shortcuts

| Shortcut | 动作 | 谁用 |
|----------|------|------|
| `+issue` | 自然语言 → 结构化 GitHub Issue（角色模板自动匹配） | 全员 |
| `+branch` | 从 Issue 编号创建 `issue-N-slug` 分支 | 工程/算法 |
| `+quick` | 一句话描述 → `hotfix/<slug>` 分支，**跳过 Issue** | 工程 |
| `+pr` | **先本地跑 CI 门禁**，过了再创建 PR（body 从 commits 生成，自动关联 Issue） | 工程/算法 |
| `+merge` | merge PR + 自动检查并同步 CLAUDE.md / PLAN.md | 工程/算法 |
| `+ci` | **本地探测并跑 CI 校验**，定位失败、输出修复建议（GitHub 日志降级为补充） | 工程 |
| `+status` | 全局进展速查：open issues / PRs / main CI 状态 | 全员 |
| `+release` | 从 merged PRs 生成分类发版说明 | PM/工程 |

---

## 决策矩阵

按用户描述自动匹配，**命中即执行，无需用户指定 shortcut**。

| 用户说 | 执行 |
|--------|------|
| "有个新功能想法…" / "用户反馈说…" | `+issue`，PM 模板 |
| "发现一个 bug，复现步骤是…" | `+issue`，Engineering 模板 |
| "想做个实验验证假设…" | `+issue`，Algorithm Spike 模板 |
| "运营流程需要调整…" | `+issue`，Ops 模板 |
| "客户/商务有个需求…" | `+issue`，Business 模板 |
| "开始做 Issue #7" / "基于 #7 开分支" | `+branch` |
| "小改动" / "顺手修一下" / "不值得开 issue" | `+quick` → `hotfix/` 分支，无 issue |
| "改完了" / "要提 PR" / "可以 review 了" | `+pr`（含本地 CI 前置门禁） |
| "merge PR #N" / "合并 PR" / "PR 合并进 main" | `+merge` |
| "CI 红了" / "CI 失败" / "tests failing" / "本地跑下 CI" / "提 PR 前先校验" | `+ci`（本地跑） |
| "项目啥进展" / "open issues 有哪些" | `+status` |
| "准备发版" / "写 changelog" / "release notes" | `+release` |

---

## Red Flags — 立刻停止

- 手动跑 `gh pr merge` 而不用 `+merge` → 会跳过文档同步
- PR merge 后说"文档下次再更新" → 不存在"下次"，现在就是最佳时机
- CLAUDE.md 或 PLAN.md 超过 2 个 PR 没更新 → 立刻跑 `+merge` 补回
- **先建 PR 再等 GitHub 告诉我 CI 红没红** → 反模式。CI 前置到本地：`+pr` 建 PR 前先本地跑过
- **因 GitHub Actions 没跑/红就卡住不合并**（实际是 billing/额度问题）→ 以本地 CI 为准，别被远端阻塞

---

## 详细操作文档

- [`+issue` 创建流程](references/tc-issue-create.md)
- [角色模板库（PM/Engineering/Ops/Business/Algorithm）](references/tc-issue-templates.md)
- [`+branch` / `+quick` 分支规范](references/tc-branch-workflow.md)
- [`+pr` 创建流程](references/tc-pr-create.md)
- [`+merge` 流程 + 文档同步](references/tc-sync-docs.md)
- [本地 CI 探测与运行（`+pr` 前置门禁 / `+ci` 默认路径）](references/tc-local-ci.md)
- [`+ci` 失败分析](references/tc-ci-debug.md)
- [`+status` / `+release`](references/tc-status.md)

---

## 前置要求

```bash
gh auth status          # 确认已登录 gh CLI
git remote get-url origin  # 确认当前目录是 git repo
```
