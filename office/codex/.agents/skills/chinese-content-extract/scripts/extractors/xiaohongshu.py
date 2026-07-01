"""小红书笔记内容抽取器。

三层降级：
  Tier 1 - xhs PyPI 库（需 XHS_COOKIE 环境变量）
  Tier 2 - Playwright 无头浏览器（无需 cookie，速度慢）
  Tier 3 - 提示用户配置 cookie
"""
from __future__ import annotations

import datetime
import os
import re

from extractors.base import ArticleExtractor

# 匹配 24 位十六进制 note_id
_NOTE_ID_RE = re.compile(r"(?<![a-f0-9])([a-f0-9]{24})(?![a-f0-9])")

# skill 目录下的 config.env 优先，环境变量作为 fallback
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_FILE = os.path.join(_SKILL_DIR, "config.env")

def _load_cookie() -> str:
    """优先读 skill 目录下的 config.env，fallback 到环境变量。"""
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("XHS_COOKIE="):
                    return line[len("XHS_COOKIE="):].strip()
    return os.environ.get("XHS_COOKIE", "")


def _expand_short_link(url: str) -> str:
    """展开 xhslink.com 短链，返回完整 URL 或原 URL。"""
    if "xhslink.com" not in url:
        return url
    try:
        import requests
        r = requests.get(url, allow_redirects=True, timeout=8,
                         headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"})
        return r.url
    except Exception:
        return url


def _ts_to_date(ts) -> str:
    """毫秒或秒时间戳转 YYYY-MM-DD。"""
    try:
        ts = int(ts)
        if ts > 10**12:
            ts //= 1000
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return ""


class XiaohongshuExtractor(ArticleExtractor):
    """小红书笔记抽取器（xiaohongshu.com / xhslink.com 短链）。"""

    def matches(self, url: str) -> bool:
        return "xiaohongshu.com" in url or "xhslink.com" in url

    def extract(self, url: str) -> dict:
        # 短链展开
        resolved = _expand_short_link(url)

        # 提取 note_id
        m = _NOTE_ID_RE.search(resolved)
        note_id = m.group(1) if m else None

        # Tier 1：带 cookie fetch 页面解析 INITIAL_STATE（短链直接访问，绕境外限制）
        cookie = _load_cookie().strip()
        if cookie:
            result = self._extract_xhs_lib(note_id, url, cookie)
            if result is not None:
                return result

        # Tier 2：trafilatura 直接 fetch 原始 URL（对 xhslink.com 短链效果好）
        result = self._extract_trafilatura(url)
        if result is not None:
            return result

        # Tier 3：Playwright（桌面 UA，慢但覆盖更多情况）
        result = self._extract_playwright(note_id, resolved)
        if result is not None:
            return result

        # Tier 3：无法抓取，提示配置
        return {
            "platform": "xiaohongshu",
            "error": (
                "无法抓取小红书内容。小红书有强反爬措施，需配置 XHS_COOKIE 才能稳定读取。\n"
                "配置方法：浏览器登录 xiaohongshu.com → F12 → Application → Cookies，"
                "复制 a1、web_session、webId 三个字段，在 jack profile .env 中加入：\n"
                "XHS_COOKIE=a1=xxx; web_session=yyy; webId=zzz"
            ),
            "url": url,
        }

    # ------------------------------------------------------------------
    # Tier 1：带 cookie 直接 fetch 笔记页面，解析 window.__INITIAL_STATE__
    # ------------------------------------------------------------------
    def _extract_xhs_lib(self, note_id: str | None, original_url: str, cookie: str) -> dict | None:
        try:
            import requests as _req
            import json as _json
        except ImportError:
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Cookie": cookie,
            "Referer": "https://www.xiaohongshu.com/",
        }
        # 优先访问原始 URL（短链 xhslink.com/o/ 在境外可用），再试 /explore/
        urls_to_try = [original_url]
        if note_id:
            urls_to_try.append(f"https://www.xiaohongshu.com/explore/{note_id}")

        for fetch_url in urls_to_try:
            try:
                r = _req.get(fetch_url, headers=headers, allow_redirects=True, timeout=15)
                if r.status_code != 200:
                    continue
                html = r.text
                m = re.search(r"window\.__INITIAL_STATE__=({.+?})</script>", html)
                if not m:
                    continue
                raw = m.group(1).replace("undefined", "null")
                state = _json.loads(raw)
                note_map = (state.get("note") or {}).get("noteDetailMap", {})
                if not note_map:
                    continue
                nid = list(note_map.keys())[0]
                note = note_map[nid].get("note", {})
                if not note:
                    continue
                return self._build_result(note, original_url)
            except Exception:
                continue
        return None

    def _build_result(self, note: dict, url: str) -> dict | None:
        title = note.get("title") or ""
        desc = note.get("desc") or note.get("content") or ""
        tag_list = note.get("tagList") or note.get("tag_list") or []
        tags_str = " ".join(
            "#" + (t.get("name") or "") for t in tag_list
            if isinstance(t, dict) and t.get("name")
        )
        content = (desc + ("\n" + tags_str if tags_str else "")).strip()
        user = note.get("user") or note.get("author") or {}
        author = (user.get("nickname") or user.get("name") or "") if isinstance(user, dict) else ""
        ts = note.get("time") or note.get("createTime") or note.get("create_time") or 0
        publish_date = _ts_to_date(ts) if ts else ""
        images = note.get("imageList") or note.get("image_list") or []
        if not content and not title:
            return None
        return {
            "platform": "xiaohongshu",
            "title": title,
            "author": author,
            "publish_date": publish_date,
            "content": content[:15000],
            "word_count": len(content),
            "url": url,
            "image_count": len(images),
            "truncated": len(content) > 15000,
        }

    # ------------------------------------------------------------------
    # Tier 2：trafilatura 直接抓取（对短链效果好，无需浏览器）
    # ------------------------------------------------------------------
    def _extract_trafilatura(self, url: str) -> dict | None:
        try:
            import trafilatura  # type: ignore
        except ImportError:
            return None
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            text = trafilatura.extract(downloaded, include_comments=False, no_fallback=False)
            if not text or len(text) < 100:
                return None
            # 过滤登录页噪音
            login_noise = ["当前内容仅支持在小红书 APP 内查看", "App内打开", "登录后推荐更懂你", "手机号登录"]
            if any(n in text for n in login_noise) and len(text) < 500:
                return None
            return {
                "platform": "xiaohongshu",
                "title": "",
                "author": "",
                "publish_date": "",
                "content": text[:15000],
                "word_count": len(text),
                "url": url,
                "image_count": 0,
                "truncated": len(text) > 15000,
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Tier 3：Playwright
    # ------------------------------------------------------------------
    def _extract_playwright(self, note_id: str | None, url: str) -> dict | None:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            return None

        target = (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            if note_id
            else url
        )
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    ctx = browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1280, "height": 800},
                    )
                    page = ctx.new_page()
                    page.goto(target, timeout=30000, wait_until="networkidle")

                    title = ""
                    for sel in ("#detail-title", ".title span", ".note-text h1", "h1"):
                        try:
                            el = page.locator(sel).first
                            if el.count() > 0:
                                title = (el.inner_text(timeout=2000) or "").strip()
                                if title:
                                    break
                        except Exception:
                            continue

                    content_text = ""
                    for sel in ("#detail-desc .desc span", "#detail-desc", ".note-text", "article"):
                        try:
                            el = page.locator(sel).first
                            if el.count() > 0:
                                content_text = (el.inner_text(timeout=2000) or "").strip()
                                if content_text:
                                    break
                        except Exception:
                            continue

                    author = ""
                    for sel in (".author-wrapper .name span", ".username span", ".user-name"):
                        try:
                            el = page.locator(sel).first
                            if el.count() > 0:
                                author = (el.inner_text(timeout=2000) or "").strip()
                                if author:
                                    break
                        except Exception:
                            continue

                    if not content_text:
                        try:
                            import trafilatura  # type: ignore
                            extracted = trafilatura.extract(page.content(), include_comments=False)
                            content_text = extracted or ""
                        except Exception:
                            pass
                finally:
                    browser.close()

            if not content_text and not title:
                return None

            return {
                "platform": "xiaohongshu",
                "title": title,
                "author": author,
                "publish_date": "",
                "content": content_text[:15000],
                "word_count": len(content_text),
                "url": url,
                "image_count": 0,
                "truncated": len(content_text) > 15000,
            }
        except Exception:
            return None
