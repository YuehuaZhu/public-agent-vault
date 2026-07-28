---
name: viewmind-context
description: Use when the user asks about recent work, commits, browsing history, or AI sessions — or when you need context about current projects and interests. Triggers: 最近在做什么, 我研究过什么, 最近提交了什么, what have I been working on, search my context, 搜索上下文, recent git commits, recent browser history.
---

# ViewMind Context

用户的个人 context 存储(git 提交 / 浏览研究 / AI 对话)。`viewmind-hub` CLI 查询。

## 路由表

| 意图 | 命令 |
|---|---|
| 最近在哪些项目提交了代码? | `viewmind-hub recent --type git` |
| 最近浏览/研究了什么? | `viewmind-hub recent --type browser` |
| 最近的 AI 对话上下文? | `viewmind-hub recent --type claude-session` |
| 所有类型最近记录 | `viewmind-hub recent` |
| 搜索关于 X 的上下文 | `viewmind-hub search "X"` |
| 某类型内搜索 | `viewmind-hub search "X" --type git` |
| 控制条数(默认 10/20) | 追加 `--limit N` |
| 我的知识图谱里有哪些节点? | `viewmind-hub graph` |
| 只看浏览器来源的知识节点 | `viewmind-hub graph --channel browser` |
| 只看开发/AI 对话来源的节点 | `viewmind-hub graph --channel claude-code` |
| 搜索图谱中关于 X 的节点 | `viewmind-hub graph --keyword "X"` |
| 只看公开级别的知识节点 | `viewmind-hub graph --version public` |
| 组合过滤 | `viewmind-hub graph --channel browser --keyword "sigma" --limit 20` |

## 输出格式

每条一行,可直接用于回答:

```
[git]     2026-05-29  ViewMindDesktopHub:main  commit abc1234  "feat: R2.5 Git Collector"
[browser] 2026-05-29  sigma.js docs            "Force-directed graph layouts with ForceAtlas2"
[session] 2026-05-29  ViewMindDesktopHub       45msgs  "Implementing R2.5 collector protocol"
```

## 使用规范

1. 跑路由表命令 → 得紧凑列表
2. 综合成回答 — 不要把原始输出直接扔给用户

## 错误处理

- 命令失败/无输出 → hub 可能离线,告知用户运行 `pnpm serve` 或打开 DesktopHub 应用
- 无结果 → 改用 `search` 换关键词,或去掉 `--type` 扩大范围
