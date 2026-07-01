# Office 配置包（文职精简版）

面向**非技术背景的文职人员**的一套开箱即用 Agent 配置。是 `builder/` 完整技术版的精简子集：去掉了 git / GitHub / CI / 代码研发相关的技能与规范，只保留日常办公用得上的部分（写作、调研、飞书操作、内容总结、想法梳理）。

同时支持 **Claude Code** 和 **Codex** 两种工具，内容保持一致。

## 目录结构

```
office/
├── claude/.claude/          # Claude Code 用
│   ├── CLAUDE.md            # 指令规范（精简版）
│   ├── settings.json        # 权限 + 会话大小提醒 hook
│   ├── hooks/               # session-size-warn.sh
│   └── skills/              # 5 个通用 skill
├── codex/                   # Codex 用
│   ├── .codex/AGENTS.md     # 指令规范（与 CLAUDE.md 同源）
│   └── .agents/skills/      # 与 claude 侧一致的 5 个 skill
├── manifest.json            # skill 清单 + 版本号（IT 推送依据）
└── README.md               # 本文件
```

## 包含的 5 个 Skill

| Skill | 作用 |
|---|---|
| `using-superpowers` | 入门：教助手「遇到任务先找有没有可用 skill」 |
| `chinese-content-extract` | 抓取并总结微信 / 知乎 / 小红书等中文平台文章 |
| `lark-router` | 飞书全套操作（IM / 文档 / 表格 / 日历 / 审批…） |
| `brainstorming` | 把想法聊成成形的方案 / 设计 |
| `writing-skills` | 沉淀自己的高频工作流为可复用 skill |

> 这 5 个 skill 与 `builder/` 里的**完全一致**，方便统一维护。

## 安装（IT 统一推送）

IT 以 `manifest.json` 为清单，把文件铺到员工的 home 目录：

**Claude Code 用户：**
```
office/claude/.claude/*   →   ~/.claude/
```

**Codex 用户：**
```
office/codex/.codex/*     →   ~/.codex/
office/codex/.agents/*    →   ~/.agents/
```

铺完后，用户直接打开 Claude Code / Codex 即可，skill 会被自动发现。

> 具体的批量下发方式（MDM / 脚本 / 内部工具）由 IT 按公司环境落地；本目录只约定「哪些文件放到哪里」。

## 与 builder 的关系

- `builder/`：完整技术版（22 个 skill，含 git 协同、CI、TDD、code review 等），面向工程师。
- `office/`：精简子集，面向文职。skill 是 builder 的原样拷贝，不做分叉修改——升级时从 builder 同步即可。
