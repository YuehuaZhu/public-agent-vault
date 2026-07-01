---
name: chinese-content-extract
description: "当用户发送 mp.weixin.qq.com、zhihu.com、xueqiu.com、xiaohongshu.com 或 xhslink.com 链接，或说了「总结这篇/看看这个/帮我看这个链接/这文章讲什么/这篇文章」时，调用本 skill 的 scripts/fetch.py 抓取内容。不适用：用户要搜索信息或打开网页交互。"
version: 3.0.0
tags: [content, extraction, chinese, wechat, zhihu, xueqiu, xiaohongshu, article, summary]
---

<when_to_use>
用户发送以下链接时调用：
- mp.weixin.qq.com（微信公众号）
- zhihu.com（知乎专栏/问答）
- xueqiu.com（雪球）
- xiaohongshu.com / xhslink.com（小红书）
- 其他网页链接（通用 fallback）

用户说「总结这篇/看看这个/这文章/帮我看」时也调用。
消息不含 URL 但有「这篇/上面那篇/刚才那个」指代 → 先查记忆找最近链接，再调用。
</when_to_use>

<do_not>
禁止用浏览器工具（browser_navigate 等）直接打开微信/小红书链接——这些平台对自动化浏览器有严格反爬（人机验证/滑块），必失败。
fetch.py 用专用 UA 和 API 方式抓取，不需要浏览器。
</do_not>

<procedure>

## 步骤 0（消息无 URL 时）：从记忆中找最近链接

若会话记忆可用，查询最近含 URL 的消息；否则直接请用户发链接。

## 步骤 0.5（预处理微信 captcha 链接）

如果 URL 包含 `wappoc_appmsgcaptcha`：
1. 从 URL 的 `target_url` 查询参数中提取经 URL 编码的真实文章链接
2. 用解码后的 `mp.weixin.qq.com/s/` 链接执行步骤 1
3. **不要向用户索要新链接**——captcha URL 里已包含目标文章 URL

## 步骤 1：执行抽取脚本

```bash
python3 "${SKILL_ROOT:-$HOME/.claude/skills}/chinese-content-extract/scripts/fetch.py" "<url>"
```

返回 JSON：`{platform, title, author, publish_date, content, word_count, url, error}`

- `word_count > 0` 且无 `error` → 成功，进步骤 2
- 有 `error` → 告知用户原因，**不要改用浏览器重试**
- 小红书返回"需配置 XHS_COOKIE"→ 引导用户按下方配置说明操作

## 步骤 2：生成摘要

根据 content 简洁回复，提炼核心观点，避免直接复述全文：

```
📄 <标题>
<作者> · <字数>字

<300-500 字摘要>

关键观点：
- ...
```

</procedure>

<config>

### 小红书内容抓取（可选）

小红书有强反爬措施，配置以下环境变量后可稳定抓取：

```
XHS_COOKIE=a1=xxx; web_session=yyy; webId=zzz
```

获取方式：浏览器登录 xiaohongshu.com → F12 → Application → Cookies，复制 `a1`、`web_session`、`webId` 三个字段的值拼接。

Cookie 有效期约 30-60 天，过期后重新获取即可。未配置时自动降级为 Playwright 渲染或提示配置。

</config>

<pitfalls>
- **微信 captcha 跳转链接**（URL 含 `wappoc_appmsgcaptcha`）：从 URL 的 `target_url` 参数提取真实文章链接，不要报错，不要问用户重发。
- **小红书短链（xhslink.com）**：fetch.py 自动展开，直接传原始链接即可。
- **知乎部分内容需登录**：抽取可能不全，正常现象，如实告知。
- **境外网络访问限制**：国外服务器直接访问 xiaohongshu.com/explore/ 路径受限，fetch.py 已处理（优先访问原始短链绕限）。
- **fetch.py 返回空内容时的诊断**：
  1. 含 `环境异常` → captcha 拦截，从 URL 提取 target_url 重试
  2. `og:description/og:image` 有值但内容空 → 脚本解析问题
  3. `og:description=""` 且无 captcha → 文章已删或需关注可见
- **内容很长时**：提炼核心观点，不要全文复述。
</pitfalls>
