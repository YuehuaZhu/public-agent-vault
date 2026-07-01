# +new — 创建新仓库并写入全部必备文件

## 流程

```bash
# 1. 收集信息
# - 仓库名（kebab-case）
# - 一句话描述
# - 可见性：public / private（默认 private）
# - 主语言（用于 CI 模板选择）

# 2. 创建 GitHub 仓库
gh repo create <name> \
  --description "<description>" \
  --private \
  --clone

cd <name>

# 3. 写入必备文件（见各模板）
# CLAUDE.md / README.md / PLAN.md / .github/

# 4. 初始提交
git add .
git commit -m "chore: repo-init — 初始化项目骨架"
git push -u origin main

# 5. 设置 branch protection（main 分支）
gh api repos/<owner>/<name>/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":0}' \
  --field restrictions=null
```

## 输出

```
✅ 仓库已创建：https://github.com/<owner>/<name>
✅ 写入文件：CLAUDE.md / README.md / PLAN.md / .github/workflows/ci.yml / .github/ISSUE_TEMPLATE/
✅ main 分支保护已开启
```

## 填写提示

创建前向用户确认：
1. **仓库名**（不能包含空格，建议 kebab-case）
2. **项目描述**（一句话，写进 README 第一行）
3. **主要语言/框架**（影响 CI 模板：Python / Node.js / Go / 其他）
4. **public 还是 private**（默认 private）
