# +merge — Merge PR + 文档同步

## The Iron Law

```
PR merge 后不更新 CLAUDE.md 和 PLAN.md = 文档欠债。
欠债累积 = 下一个接手者（包括你自己）看到的是谎言。
MUST 使用 +merge，NEVER 手动 gh pr merge。
```

---

## 何时使用

- 本地 CI 已通过（`+pr` 的 Step 0 前置门禁跑过；保险可重跑一遍 [本地 CI](tc-local-ci.md)），PR 准备合并时
- **替代**手动 `gh pr merge`，不是额外步骤

> **不阻塞在 GitHub Actions 上**：以本地 CI 结果为合并门禁。GitHub CI 能跑时是额外确认，跑不起来（billing/额度/网络）不阻塞合并。

## 何时不需要

- PR 仅改了测试文件且架构无变化（仍建议跑，可能 0 秒结束）
- 文档类 PR 本身就是在更新 CLAUDE.md / PLAN.md（避免循环）

---

## 完整流程

### Step 1：Merge PR

```bash
# 获取 PR 编号（若未提供）
gh pr list --state open

# 记下 PR 对应的源分支（merge 后用它来删本地 + 远端）
branch_name=$(gh pr view <N> --json headRefName --jq .headRefName)

# Merge（rebase 保留 commit 语义）
gh pr merge <N> --rebase
```

> 若分支保护因「必需的状态检查未通过」挡住合并，而本地 CI 已绿、远端只是因 billing/额度没跑：仓库 owner 可加 `--admin` 绕过（`gh pr merge <N> --rebase --admin`）。仅在本地 CI 确认通过后才这么做。

### Step 2：拉取最新 main

```bash
git checkout main
git pull
```

### Step 3：分析本次 PR 变更

```bash
# 查看本次 PR 引入的所有变更
git log HEAD~<commit数>..HEAD --oneline
git diff HEAD~<commit数>..HEAD --name-only
```

### Step 4：评估 CLAUDE.md 是否需要更新

逐项检查，任意一项为「是」则需要更新：

| 检查项 | 需要更新？ |
|--------|---------|
| 架构或模块结构有变化（新增/删除子系统） | 是 |
| 目录结构有变化（新增/删除重要目录或文件） | 是 |
| 关键命令或配置路径有变化 | 是 |
| 新的已知限制、约束或排障步骤 | 是 |
| 仅改了业务逻辑，架构无变化 | 否 |

**✅ Good — 需要更新的情况：**
```
PR 新增了 framework/worktree-activate.sh
→ CLAUDE.md 目录结构章节需加此文件说明
→ 运维命令速查需加使用示例
```

**❌ Bad — 不需要更新的情况：**
```
PR 修复了一个函数内部的 bug
→ 不涉及架构/命令/限制，跳过 CLAUDE.md 更新
```

### Step 5：评估 PLAN.md 是否需要更新

PLAN.md 分两部分独立评估：

**① 主线计划**

| 检查项 | 需要更新？ |
|--------|---------|
| 某个 Stage 的任务全部完成 | 是 → 标记为 ✅ 完成 |
| 当前 Stage 目标或验收标准有调整 | 是 |
| 需要新开下一个 Stage | 是 |

**② 支线计划**

| 检查项 | 需要更新？ |
|--------|---------|
| 本次 PR 启动了一个新的调研/实验/优化方向 | 是 → 新增支线记录 |
| 某个支线已完成或放弃 | 是 → 标记或移除 |
| 本次 PR 只是推进已知任务，支线无变化 | 否 |

### Step 6：展示变更建议并确认

若 Step 4 或 Step 5 有需要更新的项，展示具体变更内容：

```
📋 建议更新 CLAUDE.md：
  - 目录结构章节：新增 framework/worktree-activate.sh 说明
  - 运维命令：新增 worktree 使用示例

📋 建议更新 PLAN.md：
  - 主线：Stage 2 任务「外置 runtime 路径」标记为完成
  - 支线：新增「worktree 支持」方向（本次 PR 启动）

确认更新？(y/n/跳过某项)
```

### Step 7：执行更新并推送

用户确认后：

```bash
# 编辑 CLAUDE.md 和/或 PLAN.md
# 然后提交
git add CLAUDE.md PLAN.md
git commit -m "docs: sync CLAUDE.md and PLAN.md after PR #<N>"
git push origin main
```

**若无需更新：**
```
✅ 文档无需更新，本次 PR 未引入架构或计划变化。
```

### Step 8：自动清理分支（远端 + 本地）

文档同步完成（或确认无需更新）后，清理这条已 merge 的工作分支：

```bash
# 当前应在 main（Step 2 已切过）；保险再确认一次
git checkout main

# 1. 删远端分支（幂等：已不存在则跳过，例如 GitHub 配了 Auto-delete）
git push origin --delete "$branch_name" 2>/dev/null \
  && echo "✅ 远端分支 $branch_name 已删除" \
  || echo "ℹ️ 远端分支 $branch_name 已不存在，跳过"

# 2. 删本地分支（幂等）
if git show-ref --verify --quiet "refs/heads/$branch_name"; then
  git branch -D "$branch_name"
  echo "✅ 本地分支 $branch_name 已删除"
else
  echo "ℹ️ 本地分支 $branch_name 不存在，跳过"
fi
```

> `+merge` 完成后，刚才那条工作分支会从远端和本地同时消失，`git branch` 看不到它了。
> 这是设计内的——分支生命周期 = 一次 PR。后续改动用 `+branch` / `+quick` 新建。

---

## 输出格式

成功更新：
```
✅ PR #<N> 已 merge
✅ CLAUDE.md 已更新：[具体更新了什么]
✅ PLAN.md 已更新：[具体更新了什么]
✅ 文档 commit 已推送 main
✅ 分支 <branch_name> 已从远端和本地清理
```

无需更新：
```
✅ PR #<N> 已 merge
✅ 文档无需更新
✅ 分支 <branch_name> 已从远端和本地清理
```

---

## Red Flags

- 手动跑 `gh pr merge` 跳过此流程 → 文档欠债
- 说"这次改动很小不用更新" → MUST 跑 Step 4/5 确认，不能凭感觉判断
- CLAUDE.md 超过 3 个 PR 没动 → 可能欠债了，手动触发 `+merge` 补回

---

## 常见理由 vs 现实

| 理由 | 现实 |
|------|------|
| "这次改动太小了" | Step 4/5 判断需 30 秒，跑一遍不吃亏 |
| "文档等下次一起更" | 不存在"下次"，下次又有新 PR，永远追不上 |
| "CLAUDE.md 大家都不看" | 你下次让 Claude 帮你看项目时，它会看 |
| "PLAN.md 我自己记得" | 你记得，Claude 不记得 |
