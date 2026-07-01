---
name: lark-router
version: 1.0.0
description: "飞书 API 统一路由表：所有飞书操作的单一入口。读此文件获取模块路径、关键命令和语法。需要更深的参数说明时，再读对应模块的 SKILL.md 或 references/。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 飞书 API 路由表

## 0. 认证前提（所有操作必读）

**任何操作前** 先读 [`lark-shared/SKILL.md`](lark-shared/SKILL.md)，了解：
- `--as user`（用户身份）vs `--as bot`（应用身份）的选择
- `lark-cli auth login`（user 身份授权）
- `lark-cli config init`（首次配置）
- Permission denied 错误处理

---

## 1. 路由表

### 即时通讯（lark-im）
深度文档：[`lark-im/SKILL.md`](lark-im/SKILL.md)

| 意图 | 命令 |
|------|------|
| 发消息到群/私聊 | `lark-cli im +messages-send --chat-id <oc_xxx> --text "内容"` |
| 回复消息 | `lark-cli im +messages-reply --message-id <om_xxx> --text "内容"` |
| 搜索聊天记录 | `lark-cli im +messages-search --query "关键词"` |
| 列出群消息 | `lark-cli im +chat-messages-list --chat-id <oc_xxx>` |
| 列出群成员 | `lark-cli im +chat-search --query "群名"` |
| 创建群聊 | `lark-cli im +chat-create --name "群名"` |
| 添加表情回复 | `lark-cli im +reactions --message-id <om_xxx> --emoji "THUMBSUP"` |
| 下载图片/文件 | `lark-cli im +messages-resources-download --message-id <om_xxx>` |

---

### 云文档（lark-doc）
深度文档：[`lark-doc/SKILL.md`](lark-doc/SKILL.md)
> ⚠️ 所有命令必须携带 `--api-version v2`

| 意图 | 命令 |
|------|------|
| 读取文档内容 | `lark-cli docs +fetch --api-version v2 --doc "<URL或token>"` |
| 创建文档 | `lark-cli docs +create --api-version v2 --content '<title>标题</title><p>内容</p>'` |
| 追加内容 | `lark-cli docs +update --api-version v2 --doc "<URL>" --command append --content '<p>内容</p>'` |
| 精准替换内容 | `lark-cli docs +update --api-version v2 --doc "<URL>" --command str_replace --old "旧文字" --new "新文字"` |
| 搜索云空间文档 | `lark-cli docs +search --query "关键词"` |
| 上传图片到文档 | `lark-cli docs +media-insert --doc "<URL>" --file ./image.png` |
| 下载文档中素材 | `lark-cli docs +media-download --doc "<URL>"` |

---

### 电子表格（lark-sheets）
深度文档：[`lark-sheets/SKILL.md`](lark-sheets/SKILL.md)

| 意图 | 命令 |
|------|------|
| 创建表格 | `lark-cli sheets +create --title "表名"` |
| 读取单元格 | `lark-cli sheets +read --sheet "<URL>" --range "Sheet1!A1:C10"` |
| 写入数据 | `lark-cli sheets +write --sheet "<URL>" --range "A1" --values '[["标题1","标题2"]]'` |
| 追加行 | `lark-cli sheets +append --sheet "<URL>" --range "Sheet1" --values '[["值1","值2"]]'` |
| 搜索内容 | `lark-cli sheets +find --sheet "<URL>" --query "关键词"` |
| 导出为文件 | `lark-cli sheets +export --sheet "<URL>" --type xlsx` |

---

### 多维表格 Base（lark-base）
深度文档：[`lark-base/SKILL.md`](lark-base/SKILL.md)
> 导入 Excel/CSV 先用 `lark-cli drive +import --type bitable`，再用 base 命令操作

| 意图 | 命令 |
|------|------|
| 列出记录 | `lark-cli base +record-list --base "<URL>" --table <table_id>` |
| 查询/搜索记录 | `lark-cli base +record-search --base "<URL>" --table <table_id> --filter '...'` |
| 新增记录 | `lark-cli base +record-batch-create --base "<URL>" --table <table_id> --records '[{...}]'` |
| 更新记录 | `lark-cli base +record-batch-update --base "<URL>" --table <table_id> --records '[{...}]'` |
| 插入或更新 | `lark-cli base +record-upsert --base "<URL>" --table <table_id>` |
| 列出字段 | `lark-cli base +field-list --base "<URL>" --table <table_id>` |
| 创建字段 | `lark-cli base +field-create --base "<URL>" --table <table_id> --name "字段名" --type text` |
| 数据统计分析 | `lark-cli base +data-query --base "<URL>" --table <table_id>` |

---

### 日历/日程（lark-calendar）
深度文档：[`lark-calendar/SKILL.md`](lark-calendar/SKILL.md)
> 查询**已结束**的会议 → 用 lark-vc 而非 lark-calendar

| 意图 | 命令 |
|------|------|
| 查看今日/近期日程 | `lark-cli calendar +agenda` |
| 创建日程 | `lark-cli calendar +create --title "标题" --start "2026-05-09T10:00:00+08:00" --end "..."` |
| 查询忙闲 | `lark-cli calendar +freebusy --start <time> --end <time>` |
| 回复日程邀请 | `lark-cli calendar +rsvp --event-id <id> --status accept` |
| 查找可用会议室 | `lark-cli calendar +room-find`（⚠️ 必须先读 references/lark-calendar-schedule-meeting.md） |
| 智能推荐空闲时段 | `lark-cli calendar +suggestion` |

---

### 云空间/文件管理（lark-drive）
深度文档：[`lark-drive/SKILL.md`](lark-drive/SKILL.md)

| 意图 | 命令 |
|------|------|
| 上传文件 | `lark-cli drive +upload --file ./file.pdf --folder-token <token>` |
| 下载文件 | `lark-cli drive +download --token <file_token>` |
| 创建文件夹 | `lark-cli drive +create-folder --name "文件夹名" --parent-token <token>` |
| 移动文件 | `lark-cli drive +move --token <token> --folder-token <target>` |
| 删除文件 | `lark-cli drive +delete --token <token>` |
| 导入本地文件为飞书文档 | `lark-cli drive +import --file ./doc.docx --type docx` |
| 导出飞书文档为本地文件 | `lark-cli drive +export --token <token> --type pdf` |
| 修改文件标题 | `lark-cli drive +rename --token <token> --title "新标题"` |
| 管理文档权限 | `lark-cli drive +apply-permission --token <token>` |

---

### 知识库 Wiki（lark-wiki）
深度文档：[`lark-wiki/SKILL.md`](lark-wiki/SKILL.md)

| 意图 | 命令 |
|------|------|
| 列出知识空间 | `lark-cli wiki spaces list` |
| 查看节点 | `lark-cli wiki spaces get_node --space-id <id> --token <token>` |
| 创建节点 | `lark-cli wiki +node-create --space-id <id> --title "标题"` |
| 移动节点 | `lark-cli wiki +move --space-id <id> --node-token <token>` |

---

### 任务/待办（lark-task）
深度文档：[`lark-task/SKILL.md`](lark-task/SKILL.md)

| 意图 | 命令 |
|------|------|
| 创建任务 | `lark-cli task +create --title "任务名" --due "2026-05-10"` |
| 查看我的任务 | `lark-cli task +get-my-tasks` |
| 完成任务 | `lark-cli task +complete --task-id <id>` |
| 搜索任务 | `lark-cli task +search --query "关键词"` |
| 创建任务清单 | `lark-cli task +tasklist-create --name "清单名"` |

---

### 视频会议记录（lark-vc）
深度文档：[`lark-vc/SKILL.md`](lark-vc/SKILL.md)
> 查**未来**日程用 lark-calendar；查**已结束**会议记录用此模块

| 意图 | 命令 |
|------|------|
| 搜索会议记录 | `lark-cli vc +search --start-time <ts> --end-time <ts>` |
| 获取会议纪要 | `lark-cli vc +notes --meeting-id <id>` |
| 获取逐字稿 | `lark-cli vc +recording --meeting-id <id>` |

---

### 幻灯片（lark-slides）
深度文档：[`lark-slides/SKILL.md`](lark-slides/SKILL.md)

| 意图 | 命令 |
|------|------|
| 创建演示文稿 | `lark-cli slides +create --title "标题"` |
| 读取幻灯片内容 | `lark-cli slides +xml-presentations-get --presentation-id <id>` |
| 新增页面 | `lark-cli slides +xml-presentation-slide-create --presentation-id <id>` |
| 替换页面内容 | `lark-cli slides +xml-presentation-slide-replace --presentation-id <id> --slide-id <id>` |

---

### 画板（lark-whiteboard）
深度文档：[`lark-whiteboard/SKILL.md`](lark-whiteboard/SKILL.md)

| 意图 | 命令 |
|------|------|
| 查询画板内容 | `lark-cli whiteboard +query --whiteboard-id <id>` |
| 导出画板为图片 | `lark-cli whiteboard +export --whiteboard-id <id>` |
| 用 DSL 更新画板 | `lark-cli whiteboard +update --whiteboard-id <id> --dsl '...'` |
| 用 Mermaid 更新 | `lark-cli whiteboard +update --whiteboard-id <id> --mermaid '...'` |

---

### 邮件（lark-mail）
深度文档：[`lark-mail/SKILL.md`](lark-mail/SKILL.md)

| 意图 | 命令 |
|------|------|
| 发送邮件 | `lark-cli mail +send --to "xxx@lark.com" --subject "主题" --body "内容"` |
| 查看收件箱 | `lark-cli mail +messages --folder inbox` |
| 回复邮件 | `lark-cli mail +reply --message-id <id> --body "内容"` |
| 转发邮件 | `lark-cli mail +forward --message-id <id> --to "xxx@lark.com"` |
| 起草邮件 | `lark-cli mail +draft-create --subject "主题" --body "内容"` |
| 搜索邮件 | `lark-cli mail +messages --query "关键词"` |

---

### 妙记（lark-minutes）
深度文档：[`lark-minutes/SKILL.md`](lark-minutes/SKILL.md)

| 意图 | 命令 |
|------|------|
| 搜索妙记 | `lark-cli minutes +search --query "关键词"` |
| 获取 AI 总结 | `lark-cli minutes +notes --minute-token <token>` |
| 下载音视频 | `lark-cli minutes +download --minute-token <token>` |

---

### 审批（lark-approval）
深度文档：[`lark-approval/SKILL.md`](lark-approval/SKILL.md)

| 意图 | 命令 |
|------|------|
| 查询审批实例 | `lark-cli approval instances list --approval-code <code>` |
| 查看我的审批任务 | `lark-cli approval tasks list` |

---

### 考勤（lark-attendance）
深度文档：[`lark-attendance/SKILL.md`](lark-attendance/SKILL.md)

| 意图 | 命令 |
|------|------|
| 查询打卡记录 | `lark-cli attendance records list` |

---

### OKR（lark-okr）
深度文档：[`lark-okr/SKILL.md`](lark-okr/SKILL.md)

| 意图 | 命令 |
|------|------|
| 查看 OKR 周期 | `lark-cli okr +cycle-list` |
| 查看目标详情 | `lark-cli okr +cycle-detail --period-id <id>` |

---

### 通讯录/组织架构（lark-contact）
深度文档：[`lark-contact/SKILL.md`](lark-contact/SKILL.md)

| 意图 | 命令 |
|------|------|
| 获取当前用户信息 | `lark-cli contact +get-user` |
| 按姓名/邮箱搜索员工 | `lark-cli contact +search-user --query "张三"` |

---

### 事件订阅（lark-event）
深度文档：[`lark-event/SKILL.md`](lark-event/SKILL.md)

| 意图 | 命令 |
|------|------|
| 实时监听飞书消息 | `lark-cli event +subscribe --route "im.message.receive_v1"` |
| 监听指定类型事件 | `lark-cli event +subscribe --route "<event_type>" --compact` |

---

### 原生 OpenAPI（lark-openapi-explorer）
深度文档：[`lark-openapi-explorer/SKILL.md`](lark-openapi-explorer/SKILL.md)
> 当现有 lark-cli 命令无法覆盖需求时使用

| 意图 | 命令 |
|------|------|
| 调用任意 OpenAPI | `lark-cli api GET /open-apis/<path>` |
| 带 body 调用 | `lark-cli api POST /open-apis/<path> --body '{"key":"value"}'` |

---

## 2. 工作流 Skill

| 工作流 | 说明 | 入口 |
|--------|------|------|
| 会议纪要整理 | 汇总一段时间内的会议纪要，生成结构化报告 | [`lark-workflow-meeting-summary/SKILL.md`](lark-workflow-meeting-summary/SKILL.md) |
| 日程待办摘要 | 生成今日/本周日程 + 未完成任务摘要 | [`lark-workflow-standup-report/SKILL.md`](lark-workflow-standup-report/SKILL.md) |
| 自定义 Skill 制作 | 封装新的飞书 API 操作为可复用 Skill | [`lark-skill-maker/SKILL.md`](lark-skill-maker/SKILL.md) |

---

## 3. 快速决策

```
需要发消息/看聊天记录    → lark-im
需要创建/编辑/读取文档  → lark-doc（必须 --api-version v2）
需要操作表格数据        → lark-sheets（普通表格）/ lark-base（多维表格）
需要查日程/创建会议     → lark-calendar（未来）/ lark-vc（已结束会议记录）
需要管理云空间文件      → lark-drive
需要知识库操作          → lark-wiki
需要任务管理            → lark-task
需要发邮件/看邮件       → lark-mail
需要查会议纪要/AI总结   → lark-vc（视频会议）/ lark-minutes（妙记）
需要查人/组织架构       → lark-contact
需要实时监听飞书事件    → lark-event
需要操作审批            → lark-approval
需要看考勤              → lark-attendance
需要OKR管理             → lark-okr
需要幻灯片              → lark-slides
需要画板                → lark-whiteboard
API 未封装的原始操作    → lark-openapi-explorer
身份/权限/首次配置      → lark-shared（所有操作的前提）
```
