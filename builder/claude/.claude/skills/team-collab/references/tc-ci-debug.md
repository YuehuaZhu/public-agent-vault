# +ci — 本地跑 CI 校验 + 失败分析

## 本地优先（默认路径）

**`+ci` 默认在本地跑 CI 校验，而不是去等/读 GitHub Actions。** GitHub Actions 会因 billing、额度、网络而压根跑不起来；本仓库 CI 通常只是 lint/typecheck/测试/i18n 这类静态检查，本地秒级离线就能复刻。

```
1. 探测仓库实际跑什么 CI（读 .github/workflows + package.json 脚本）
2. 本地按顺序跑，遇错即停
3. 失败 → 分类分析 + 修复建议
4. （仅当 GitHub Actions 确实跑了且失败时）才去读它的远端日志
```

### Step 1 — 本地跑 CI

**REQUIRED：** 按 [本地 CI 探测与运行](tc-local-ci.md) 探测命令并本地执行。不要硬编码某项目的命令——探测当前仓库。

- 全过 → 输出 ✅，结束（无需碰 GitHub）。
- 有失败 → 拿到失败步骤的本地输出，进入下面的 Step 3 分类分析。

### Step 2（可选，降级）— 读 GitHub 远端日志

**仅在以下情况才用**：本地全过但远端 CI 仍红（环境差异），或你明确要核对一次远端结果。

```bash
# 查看是否有远端 run（可能因 billing 根本没跑 → 直接以本地为准）
gh run list --limit 5 --json databaseId,status,conclusion,headBranch,name
gh pr checks <PR编号>        # 在 PR 上下文中
gh run view <run-id> --log-failed
```

> 若 `gh` 显示 run 因 billing/额度未启动（"recent account payments have failed" / "spending limit"），**这不是代码问题**——以本地 CI 结果为准，告知用户去处理 GitHub Billing 即可。

日志可能很长，重点看（本地输出同理）：
- 最后一个 `FAILED` 或 `ERROR` 之前的 20 行
- `AssertionError` / `SyntaxError` / `ImportError` 等异常信息
- Step 名称（定位是哪个 job/step 失败）

### Step 3 — 分类分析

#### 类型 A：单元测试失败

```
FAILED tests/unit/test_xxx.py::TestClass::test_method
AssertionError: expected X, got Y
```

分析步骤：
1. 定位失败的 test 文件和方法
2. 读取 assertion 内容（expected vs actual）
3. 判断是代码 bug 还是 test 本身过时

#### 类型 B：语法 / Import 错误

```
SyntaxError: invalid syntax
  File "xxx.py", line N
ImportError: No module named 'xxx'
```

分析步骤：
1. 从日志提取文件路径 + 行号
2. 对于 ImportError，检查是新增依赖还是路径错误

#### 类型 C：依赖安装失败

```
ERROR: Could not find a version that satisfies the requirement xxx
pip install failed
```

分析步骤：
1. 提取包名和版本要求
2. 检查 `requirements.txt` 或 `package.json`

#### 类型 D：超时

```
Error: The operation was canceled.
##[error]The job running on runner ... has exceeded the maximum execution time
```

分析步骤：
1. 找到最慢的 step（看时间戳）
2. 判断是偶发还是系统性问题

### Step 4 — 输出格式

```
❌ 失败原因：<一句话>

📍 位置：
  - 文件：<path/to/file.py>
  - 行号 / 测试：<line N 或 TestClass::test_method>

🔧 修复建议：
  <可直接执行的命令或具体代码改动>

💡 可能根因：<简短解释>
```

**示例输出：**

```
❌ 失败原因：test_docker_runner.py 中 mount 路径断言失败

📍 位置：
  - 文件：tests/unit/test_docker_runner.py
  - 测试：TestDockerRunner::test_agora_core_mount

🔧 修复建议：
  检查 lib/docker_runner.py 中 agora_core 的 mount 路径是否与测试预期一致
  运行：pytest tests/unit/test_docker_runner.py -v 本地复现

💡 可能根因：docker_runner.py 中 mount 列表改动未同步更新 test 中的预期值
```

## 判断是否偶发失败

本地 CI（lint/typecheck/i18n）是**确定性**的——重跑结果一致，几乎不存在「偶发」。直接本地重跑一遍命令即可确认：稳定失败 = 真实问题，进入分类分析。

只有涉及**网络/集成测试**的步骤才可能偶发。若是这类（且只能在 GitHub 上跑），再用远端重跑判断：

```bash
gh run rerun <run-id>          # 同一 commit 重跑
```

| 情况 | 判断 | 处理 |
|------|------|------|
| 本地稳定失败 | 真实 bug | 进入分类分析 |
| 本地通过、仅远端偶发红 | 网络/资源抖动 | 不改代码，记录即可 |
| 远端因 billing/额度未启动 | 非代码问题 | 以本地为准，提示处理 Billing |

---

## 注意

- 不要只看最后一行报错，往上找完整的 traceback
- 如果日志太长被截断，用 `gh run view <id> --log` 并 grep 关键词

---

## 自动修复：/autofix-pr

Claude Code 内置命令，比 `+ci` 更主动——CI 红了**不用手动触发**，它自己监听并提交修复 commit。

```
/autofix-pr [可选：描述修复范围]
```

适合场景：
- 简单的 lint / 格式错误
- import 路径变更导致的测试失败
- 依赖版本冲突

不适合：
- 业务逻辑 bug（需要人理解上下文）
- 架构层面的失败

---

## 依赖版本自动升级：Dependabot

CI action 版本（如 `actions/checkout@v4`）会过时。配置 Dependabot 后，每周自动开 PR 升级：

```yaml
# .github/dependabot.yml（repo-init +scaffold 自动生成）
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
  - package-ecosystem: "pip"       # 如果是 Python 项目
    directory: "/"
    schedule: { interval: "weekly" }
```

Dependabot PR 通过 CI 后直接用 `+merge` 合并即可，无需手动审查版本号。
