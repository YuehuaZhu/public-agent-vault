# +issue — 自然语言 → GitHub Issue

## 流程

```
1. 探测 repo
2. 识别角色 → 选模板
3. 填充内容
4. 建议 label
5. gh issue create
6. 输出 URL + 编号
```

### Step 1 — 探测当前 repo

```bash
git remote get-url origin
# 从 URL 提取 owner/repo，支持 https 和 ssh 格式
# https://github.com/owner/repo.git  →  owner/repo
# git@github.com:owner/repo.git      →  owner/repo
```

### Step 2 — 识别角色

从对话上下文判断说话人角色：

| 关键词/信号 | 角色 |
|------------|------|
| 用户反馈、需求、功能、PRD、验收 | PM |
| bug、报错、复现、堆栈、日志 | Engineering |
| 实验、假设、模型、指标、训练 | Algorithm |
| 流程、SOP、风险、回滚、上线 | Ops |
| 客户、商务、合同、KPI、收入 | Business |

不确定时直接问：「你是 PM / 工程 / 算法 / 运营 / 商务哪个角色？」

### Step 3 — 读取并填充模板

从 [`tc-issue-templates.md`](tc-issue-templates.md) 取对应角色模板，用用户描述的内容填充各节。

- 保持模板结构，补充用户提供的信息
- 用户没提到的字段保留占位符（如 `_待补充_`），不要删除
- title 从用户描述提炼，≤60 字符，动词开头（Add / Fix / Research / Update / Define）

### Step 4 — 建议 label

```
type:   feature | bug | research | ops | biz
priority: high | medium | low
```

根据内容判断，不确定 priority 时默认 medium。

### Step 5 — 创建 Issue

```bash
gh issue create \
  --title "<title>" \
  --body "<filled template>" \
  --label "type:<x>,priority:<y>"
```

### Step 6 — 输出

```
✅ Issue #<N> 已创建：<URL>
下一步：用 +branch 基于此 issue 开分支
```

## 注意

- 不要在未确认角色的情况下猜测并使用错误模板
- title 必须是英文或中文都可以，但要简洁有意义
- label 在 repo 不存在时 `gh issue create` 会报错，此时去掉 `--label` 参数再试，并提示用户手动在 GitHub 创建对应 label
