# +pr — 创建 Pull Request

## Step 0（前置门禁）— 本地 CI MUST 先过

**创建 PR 之前，先在本地跑一遍 CI 校验。** 这样永不推出红 PR，反馈也比等 GitHub Actions 快，且不依赖 GitHub（它可能因 billing/额度根本没跑）。

**REQUIRED：** 按 [本地 CI 探测与运行](tc-local-ci.md) 探测并运行当前仓库的 lint/typecheck/测试/i18n。

| 本地 CI 结果 | 动作 |
|--------------|------|
| ✅ 全过 | 继续创建 PR |
| ❌ 有失败 | **先修，不建 PR** → 用 [`+ci`](tc-ci-debug.md) 分析修复，修好重跑直到绿，再建 PR |
| 仓库无 CI/脚本 | 跳过门禁（无可校验项），继续 |

> 不要「先建 PR 再等 GitHub 告诉我红了」——那是旧的、依赖 GitHub 的反模式。门禁前置到本地。

---

## 自动检测轨道

根据当前分支名判断走哪条路径：

| 分支格式 | 轨道 | PR body 模式 |
|---------|------|-------------|
| `issue-<N>-*` | A（有 Issue） | `Closes #N` 或 `Part of #N`（见下） |
| `hotfix/*` | B（无 Issue） | 描述改动内容 |
| 其他格式 | 询问用户 | — |

---

## 轨道 A — issue 分支

### Step 1：判断是否多 Part issue

```bash
# 获取 issue 完整信息
gh issue view <N> --json title,body
```

**多 Part 判断条件**（满足任意一条即视为多 Part）：

1. issue body 中出现 **2 个及以上** 符合以下模式的条目：
   - `Part [A-Z]` / `Stream [A-Z]` / `Stage [0-9]` / `阶段[0-9]`
   - 或 markdown checklist：`- [ ] ...` / `- [x] ...`（含 2+ 条）
2. 已有其他 PR 合并并关联此 issue：
   ```bash
   gh pr list --search "is:merged closes:#<N> OR is:merged \"Part of #<N>\"" --json number,title
   ```

### Step 2：确定关闭关键词

| 情况 | 关键词 | 说明 |
|------|--------|------|
| 单 Part issue | `Closes #N` | 合并即关闭 issue |
| 多 Part，**非最后一个** Part | `Part of #N` | 保持 issue open |
| 多 Part，**最后一个** Part | `Closes #N` | 合并后关闭 issue |

> ⚠️ **关键词还控制 GitHub 集成测试触发**（仅当仓库配了此类 workflow，且 Actions 能跑时）：
> - `Closes #N` → 远端 CI **跑集成测试**
> - `Part of #N` → 集成测试**跳过**
> - 注意：这只影响**远端**重型测试；轻量静态检查（lint/typecheck/i18n）已在 Step 0 本地前置门禁跑过，不依赖此。

**判断"是否最后一个 Part"**：

```bash
# 查看 issue body 里的 checklist 或 Part 总数
# 查看已合并的关联 PR 数量
gh pr list --search "is:merged \"#<N>\"" --json number | jq length

# 如果：已合并 PR 数 >= 总 Part 数 - 1 → 这是最后一个 Part
# 如果无法自动判断 → 默认用 Part of #N，告知用户最后一个 Part 时改成 Closes #N
```

### Step 3：创建 PR

```bash
# 获取 commit 列表
git log main..HEAD --oneline

# 获取变更文件
git diff main..HEAD --name-only

# 创建 PR
gh pr create \
  --title "<issue title>（Part X / 最终）" \
  --body "$(cat <<'EOF'
## Summary

- <bullet 1 from commits>
- <bullet 2 from commits>

<Closes 或 Part of> #<N>

## Test plan

- [x] 本地 CI 已通过（lint/typecheck/测试/i18n，+pr 前置门禁）
- [ ] <根据变更内容补充手动验证点>
EOF
)" \
  --base main
```

### 输出示例

**非最后一个 Part：**
```
✅ PR #<M> 已创建：<URL>
Part of #<N>（issue 保持 open，还有剩余 Part）
```

**最后一个 Part：**
```
✅ PR #<M> 已创建：<URL>
Closes #<N>（merge 后自动关闭 issue）
```

---

## 轨道 B — hotfix 分支

### 流程

```bash
# 1. 从分支名提取 slug 作为 PR 标题参考
# 2. 获取 commit 列表
git log main..HEAD --oneline

# 3. 创建 PR（无 Closes #N）
gh pr create \
  --title "hotfix: <描述改动的简短标题>" \
  --body "$(cat <<'EOF'
## What changed

- <具体改了什么>

## Why

<为什么要改，问题背景>

## Test plan

- [x] 本地 CI 已通过（lint/typecheck/测试/i18n，+pr 前置门禁）
- [ ] <手动验证点>
EOF
)" \
  --base main
```

### 输出

```
✅ PR #<M> 已创建：<URL>
（无关联 Issue，追溯靠此 PR + commit 记录）
```

---

## 通用注意事项

- 创建前确认当前分支已推送到远端（`git push -u origin HEAD`）
- Summary bullets 从 commit message 提炼，不要照抄原始 commit，要有意义
- 如果只有 1 个 commit，PR title 可以直接用 commit message
- Test plan 根据 `git diff --name-only` 变更文件类型自动补充：
  - 改了 `tests/`：加「本地运行 pytest 验证」
  - 改了 `*.md`：加「检查文档渲染」
  - 改了 `*.sh`：加「bash -n 语法检查」

---

## ⚠️ PR 创建后 MUST 做的事

```
本地 CI 已在 Step 0 前置通过（这就是合并门禁，不用再等 GitHub）：

  使用 +merge 合并（不要手动 gh pr merge）

  +merge 会在 merge 完成后自动检查 CLAUDE.md 和 PLAN.md
  是否需要更新，并展示建议变更供你确认。

  跳过 +merge = 跳过文档同步 = 文档欠债
```

> GitHub Actions 能跑时是额外确认；跑不起来（billing/额度）不阻塞合并，以本地 CI 为准。

详见 [`+merge` 流程](tc-sync-docs.md)。
