# +scaffold — 对已有仓库补全缺失文件

## BLOCKING REQUIREMENT

```
CLAUDE.md 和 PLAN.md MUST 在所有其他文件之前生成。
这两个文件缺失时，流程不得跳过或延后生成。
```

---

## 流程

### Step 1：强制文件检查（阻断）

```bash
# ⭐ 强制文件：缺失则立刻生成，阻断直到完成
[ ! -f CLAUDE.md ] && BLOCKING+=("CLAUDE.md")
[ ! -f PLAN.md ]   && BLOCKING+=("PLAN.md")

if [ ${#BLOCKING[@]} -gt 0 ]; then
  echo "🚫 缺少强制文件：${BLOCKING[*]}"
  echo "   立刻生成，流程暂停直到完成..."
  # 按模板生成（见 ri-claude-md.md / ri-plan-md.md）
  # 生成完成前不进入 Step 2
fi
```

### Step 2：推荐文件检查（不阻断）

```bash
# 推荐文件：缺失则生成，但不阻断流程
[ ! -f README.md ]               && RECOMMENDED+=("README.md")
[ ! -f .github/workflows/ci.yml ] && RECOMMENDED+=(".github/workflows/ci.yml")
[ ! -d .github/ISSUE_TEMPLATE ]  && RECOMMENDED+=(".github/ISSUE_TEMPLATE/")

if [ ${#RECOMMENDED[@]} -gt 0 ]; then
  echo "⚠️ 推荐文件缺失：${RECOMMENDED[*]}，开始补全..."
  # 按各模板生成
fi
```

### Step 3：质量检查

```bash
# CLAUDE.md 存在但内容过少
if [ -f CLAUDE.md ] && [ $(wc -l < CLAUDE.md) -lt 10 ]; then
  echo "⚠️ CLAUDE.md 存在但内容少于 10 行，建议按模板补全"
fi

# CLAUDE.md 缺少「开发规范」章节 → 追加 team-collab 引用
if [ -f CLAUDE.md ] && ! grep -q "team-collab\|开发规范" CLAUDE.md; then
  echo "⚠️ CLAUDE.md 缺少开发规范章节，追加 team-collab 引用..."
fi

# README.md 存在但内容过少
if [ -f README.md ] && [ $(wc -l < README.md) -lt 5 ]; then
  echo "⚠️ README.md 存在但内容少于 5 行，是否按模板补充？(y/n)"
fi
```

### Step 4：提交

```bash
git add .
git commit -m "chore: repo-init scaffold — 补全必备文件"
git push
```

---

## 输出格式

```
🚫 强制文件缺失，立刻生成：
✅ CLAUDE.md 已生成（参考 ri-claude-md.md 模板）
✅ PLAN.md 已生成（参考 ri-plan-md.md 模板）

⚠️ 推荐文件缺失，补全中：
✅ .github/ISSUE_TEMPLATE/ 已生成（3 个角色模板）

✅ commit 已推送
```

---

## 注意事项

- 已存在的文件**不覆盖**，只补充缺失的
- CLAUDE.md 和 PLAN.md 是强制文件，NEVER 跳过
- 生成的 CLAUDE.md 必须在「开发规范」章节引用 team-collab skill
