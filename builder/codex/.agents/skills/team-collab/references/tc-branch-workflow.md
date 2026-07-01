# +branch / +quick — 分支规范

## 两种分支模式

| Shortcut | 场景 | 命名格式 | 有 Issue？ |
|----------|------|---------|-----------|
| `+branch` | 有对应 Issue 的正式开发 | `issue-<N>-<slug>` | ✅ |
| `+quick` | 小修 / Hotfix，不值得开 Issue | `hotfix/<slug>` | ❌ |

---

## +branch（轨道 A）

### Slug 生成规则

- 从 Issue title 提取 3-5 个关键词
- 全部小写，单词间用 `-` 连接（kebab-case）
- 去掉冠词（a/an/the）、介词、标点
- 中文 title 翻译成英文关键词

**示例：**

| Issue Title | 生成分支名 |
|-------------|-----------|
| Issue #7 "增加语音消息支持" | `issue-7-voice-message` |
| Issue #12 "Fix chat memory race condition" | `issue-12-chat-memory-race` |
| Issue #23 "用户登录页面 UI 优化" | `issue-23-login-page-ui` |

### 命令

```bash
# 1. 获取 issue 信息
gh issue view <N> --json title,number

# 2. 从 title 生成 slug（Claude 提取）

# 3. 远端避碰：远端已存在同名则递增后缀
proposed="issue-<N>-<slug>"
if git ls-remote --exit-code --heads origin "$proposed" >/dev/null 2>&1; then
  i=2
  while git ls-remote --exit-code --heads origin "${proposed}-${i}" >/dev/null 2>&1; do
    i=$((i+1))
  done
  branch_name="${proposed}-${i}"
  echo "⚠️ ${proposed} 远端已存在，使用 ${branch_name}"
else
  branch_name="$proposed"
fi

# 4. 创建并推送分支
git checkout -b "$branch_name"
git push -u origin "$branch_name"
```

### 输出

```
✅ 分支 issue-<N>-<slug> 已创建并推送
现在可以开始开发，改完后用 +pr 提 PR
```

---

## +quick（轨道 B）

### Slug 生成规则

- 从用户描述直接提取 3-4 个关键词
- 同样 kebab-case，全部小写

**示例：**

| 用户描述 | 生成分支名 |
|----------|-----------|
| "修一下登录页按钮对齐" | `hotfix/login-button-align` |
| "fix typo in README" | `hotfix/readme-typo` |
| "临时调一下超时阈值" | `hotfix/timeout-threshold` |

### 命令

```bash
# 远端避碰：远端已存在同名则递增后缀
proposed="hotfix/<slug>"
if git ls-remote --exit-code --heads origin "$proposed" >/dev/null 2>&1; then
  i=2
  while git ls-remote --exit-code --heads origin "${proposed}-${i}" >/dev/null 2>&1; do
    i=$((i+1))
  done
  branch_name="${proposed}-${i}"
  echo "⚠️ ${proposed} 远端已存在，使用 ${branch_name}"
else
  branch_name="$proposed"
fi

# 直接创建 hotfix 分支，不创建 Issue
git checkout -b "$branch_name"
git push -u origin "$branch_name"
```

### 输出

```
✅ 分支 hotfix/<slug> 已创建并推送（无 Issue）
改完后用 +pr 提 PR，在 PR body 里说清楚改了什么
```

---

## 注意

- 两种分支都基于最新的 `main`：执行前先 `git checkout main && git pull`
- `+quick` 不创建 Issue，PR merge 后追溯靠 PR 标题 + commit message
- 如果用户描述的改动复杂（涉及多个系统、需要多天），建议改用 `+issue` + `+branch`
- 推送前会检测远端同名分支：存在则自动加 `-2` / `-3` 后缀避碰，本地分支名同步调整
