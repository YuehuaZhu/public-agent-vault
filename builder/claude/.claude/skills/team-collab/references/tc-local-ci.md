# 本地 CI — 探测并在本地复刻仓库的 CI 校验

## 为什么本地优先

GitHub Actions 会因 billing、额度、网络、配额等原因**根本跑不起来**（拿不到任何信号）。本仓库的 CI 通常只是 lint / typecheck / 测试 / i18n 这类**静态检查**，完全可以在本地秒级、离线复刻。

**原则：本地 CI 是真相来源（source of truth），GitHub Actions 是「能跑时的额外确认」。** 不阻塞在 GitHub 上。

---

## Step 1 — 探测「CI 实际跑什么」（不要硬编码）

skill 是跨项目通用的，**必须探测当前仓库**，不能写死某个项目的命令。按以下顺序：

### 1a. 优先读 GitHub workflow（最权威——它就是 CI 的定义）

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

读主 CI workflow（通常 `ci.yml`），提取各 job 里 `run:` 步骤的命令。**只取真正的校验命令，跳过环境准备步骤**：

| 跳过（环境准备） | 保留（真正的校验） |
|------------------|--------------------|
| `actions/checkout`、`setup-node`/`setup-python` | `npm run lint` / `eslint` |
| `npm ci` / `npm install` / `pip install`（本地依赖已装好） | `npm run typecheck` / `tsc --noEmit` |
| cache、artifact 上传 | `npm test` / `pytest` |
| | `npm run i18n:check`、`npm run build` 等 |

> 依赖安装步骤本地**不重跑**（已装好，重装慢且可能触发 [[reference-ignore-scripts-broken-deps]] 之类的坑）。只跑校验命令。

### 1b. 没有 workflow 或解析不出 → 退回 package.json 脚本探测

```bash
node -e "const s=require('./package.json').scripts||{}; for(const k of ['lint','typecheck','type-check','test','test:unit','i18n:check','build','check','quality-check']) if(s[k]) console.log(k)"
```

跑存在的那些（按 lint → typecheck → i18n → test → build 的顺序）。Python 项目类比：`ruff`/`flake8` → `mypy` → `pytest`。

### 1c. 都没有 → 明确告知

> ⚠️ 仓库未发现 CI workflow，也没有 lint/typecheck/test 脚本，跳过本地 CI（无可校验项）。

---

## Step 2 — 本地按顺序跑，遇错即停

```bash
# 示例（命令来自 Step 1 探测结果，不是写死的）：
npm run lint && npm run typecheck && npm run i18n:check
```

- 串行执行，**第一个失败就停**，记下是哪一步 + 它的输出。
- 用 Node 版本对齐 CI（看 workflow 里的 `node-version` 或 `.nvmrc`；不一致时 `nvm exec <ver> ...`）。

---

## Step 3 — 输出结果

**全过：**
```
✅ 本地 CI 通过：lint ✓  typecheck ✓  i18n ✓
```

**有失败：** 进入 [`+ci` 失败分析](tc-ci-debug.md) 的分类 + 修复建议流程（同一套分析对本地输出一样适用）。

---

## 与 GitHub CI 的关系

- `+pr` **前置**跑本地 CI 当门禁：红了先修、**不建 PR**；绿了才建。
- `+merge` 以「本地 CI 已过」为准，**不阻塞**在 GitHub Actions 上（它可能因 billing 压根没跑）。
- GitHub workflow 文件**保留**：billing/配额正常时它会自动跑，是免费的二次确认，也是团队在 PR 上看到的门禁。
- 本地与 CI 环境的差异：这类静态检查（lint/typecheck/i18n）对环境不敏感，Node 版本对齐即可视为等价。涉及构建/原生模块/集成测试时，本地通过≠CI 必过，需在 PR 里说明。
