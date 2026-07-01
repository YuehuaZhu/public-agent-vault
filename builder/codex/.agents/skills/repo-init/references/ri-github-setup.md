# .github/ 配置

## 目录结构

```
.github/
├── workflows/
│   └── ci.yml                    # CI 自动化（含条件性集成测试）
├── dependabot.yml                # 依赖自动升级
└── ISSUE_TEMPLATE/
    ├── bug_report.md             # Bug 报告
    ├── feature_request.md        # 新功能
    └── config.yml                # 关闭空白 issue
```

---

## ci.yml 模板（含条件性集成测试）

### 设计原则

| Job | 触发时机 | 说明 |
|-----|---------|------|
| `test`（常驻） | 每次 push / PR | 语法 + 单元测试 + 架构约束 |
| `integration`（条件） | PR body 含 `Closes #N` | Issue 最终 PR 才跑，中间 Part 跳过 |

**强控制机制**：触发条件由 team-collab `+pr` 自动写入 PR body，不靠人记忆。

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      run_integration:
        description: '手动触发集成测试'
        type: boolean
        default: false

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # 常驻检查：每次 push / PR 必跑
  test:
    name: unit tests + syntax
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v --tb=short
      - run: bash tests/general/t1_syntax.sh

  # 集成测试：仅 Issue 最终 PR（Closes #N）触发
  integration:
    name: integration tests
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: test
    if: |
      (github.event_name == 'pull_request' &&
       contains(github.event.pull_request.body, 'Closes #')) ||
      (github.event_name == 'workflow_dispatch' &&
       github.event.inputs.run_integration == 'true')
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest tests/integration/ -v --tb=short
      # 或者：python3 tests/e2e/run_e2e.py S3 S4 S5
```

> **Node.js 版**：把 setup-python 换成 setup-node，pytest 换成 npm test

---

## dependabot.yml 模板（依赖自动升级）

每周自动开 PR 升级 GitHub Actions 版本和 pip 依赖，用 `+merge` 合并即可：

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    commit-message:
      prefix: "chore(deps)"

  - package-ecosystem: "pip"       # Python 项目
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    commit-message:
      prefix: "chore(deps)"

  # Node.js 项目改用：
  # - package-ecosystem: "npm"
```

---

## ISSUE_TEMPLATE/bug_report.md

```markdown
---
name: Bug 报告
about: 发现了不符合预期的行为
labels: bug
---

## 现象

<!-- 实际发生了什么 -->

## 复现步骤

1. 
2. 
3. 

## 期望行为

<!-- 应该发生什么 -->

## 环境

- OS：
- 版本/分支：
```

---

## ISSUE_TEMPLATE/feature_request.md

```markdown
---
name: 功能需求
about: 提出新功能或改进建议
labels: enhancement
---

## 背景

<!-- 为什么需要这个功能，解决什么问题 -->

## 方案描述

<!-- 期望的行为或实现方式 -->

## 验收标准

- [ ] 
- [ ] 

## 优先级

- [ ] 紧急（影响核心流程）
- [ ] 正常
- [ ] 低（nice to have）
```

---

## ISSUE_TEMPLATE/config.yml

```yaml
blank_issues_enabled: false
contact_links:
  - name: 文档
    url: https://github.com/<owner>/<repo>/blob/main/CLAUDE.md
    about: 查看架构文档和开发指南
```

---

## Branch Protection 设置

```bash
# PR 必须通过 CI 才能合并（via gh CLI）
gh api repos/<owner>/<repo>/branches/main/protection \
  --method PUT \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF
```
