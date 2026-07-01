# +status / +release

## +status — 全局进展速查

### 命令（并发执行）

```bash
# 1. Open Issues（带优先级分类）
gh issue list --state open --json number,title,labels,createdAt --limit 50

# 2. Open PRs（带 review 和 CI 状态）
gh pr list --state open --json number,title,reviewDecision,statusCheckRollup,headRefName

# 3. main 分支最新 CI 状态（GitHub）
gh run list --branch main --limit 1 --json status,conclusion,createdAt,name
```

> 若 GitHub Actions 因 billing/额度没跑（`gh run list` 空或显示未启动），别报「CI 红」——它只是没跑。要确认 main 健康，本地切到 main 跑一遍 [本地 CI](tc-local-ci.md) 才是真相。

### 输出格式

```
📋 Open Issues: <N>
   🔴 High:   <X 个>  — <最紧急 issue 标题>
   🟡 Medium: <Y 个>
   🟢 Low:    <Z 个>

🔀 Open PRs: <N>
   ⏳ Waiting review: <X 个>  — <PR 标题列表>
   ❌ CI failing:     <Y 个>  — <PR 标题列表>
   ✅ Ready to merge: <Z 个>

🚦 main CI: ✅ passed / ❌ failed — <时间>

📅 Last merged: <date>  <PR #N title>
```

### Priority 判断

从 issue label 中读取：
- `priority:high` 或 `priority: high` → 🔴 High
- `priority:medium` → 🟡 Medium
- `priority:low` → 🟢 Low
- 无 priority label → 归入 Medium

---

## +release — 发版说明生成

### 触发时机

用户说「准备发版」「写 changelog」「release notes」「发 v1.x」

### 命令

```bash
# 1. 获取上一个 tag
git describe --tags --abbrev=0

# 2. 获取上一个 tag 之后 merge 到 main 的 PR
gh pr list \
  --state merged \
  --base main \
  --limit 100 \
  --json number,title,mergedAt,labels,url
# 过滤 mergedAt > 上一个 tag 的时间
```

### 分类规则

从 PR label 或 title 关键词判断：

| PR 特征 | 分类 |
|---------|------|
| label `type:feature` 或 title 含 Add/New/Implement | ✨ Features |
| label `type:bug` 或 title 含 Fix/Bug/Patch | 🐛 Bug Fixes |
| label `type:research` 或 title 含 Research/Spike | 🔬 Research |
| label `type:ops` 或 title 含 Deploy/Infra/Config | 🔧 Ops & Infra |
| 其他（docs、refactor、chore 等） | 📝 Other Changes |

### 输出格式

```markdown
## v<建议版本号> — <YYYY-MM-DD>

> 共 <N> 个 PR，<X> 个功能，<Y> 个修复

### ✨ Features
- <PR title> ([#N](<URL>))

### 🐛 Bug Fixes
- <PR title> ([#N](<URL>))

### 🔧 Ops & Infra
- <PR title> ([#N](<URL>))

### 📝 Other Changes
- <PR title> ([#N](<URL>))
```

### 版本号建议

基于上一个 tag（如 `v1.2.3`）自动建议：
- 有 Feature PR → 建议 minor bump（`v1.3.0`）
- 只有 Bug Fix / Ops → 建议 patch bump（`v1.2.4`）
- 有 breaking change 信号（label 或 title 含 BREAKING）→ 建议 major bump（`v2.0.0`）

打 tag 命令（用户确认后执行）：
```bash
git tag v<X.Y.Z>
git push origin v<X.Y.Z>
```
