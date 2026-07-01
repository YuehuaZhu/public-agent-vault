"""通用 fallback 抽取器：trafilatura → Jina Reader → Playwright 三级降级。"""
from __future__ import annotations

from extractors.base import ArticleExtractor

_MAX_CONTENT = 15000

# 页面未完成 JS 渲染时的特征短语
_JS_GATE_PHRASES = frozenset([
    "you need to enable javascript",
    "please enable javascript",
    "javascript is required",
    "enable javascript",
])

# 飞书/Lark 登录页特征（未授权访问飞书内容时的跳转页）
_FEISHU_LOGIN_PHRASES = frozenset([
    "feishu - log in",
    "lark - log in",
    "feishu, first choice for front-runners",
    "切换至 lark 登录",
])


def _is_js_gate(content: str) -> bool:
    """判断内容是否为 JS 渲染门控页（未加载出真实内容）。"""
    if not content:
        return True
    return any(p in content.lower() for p in _JS_GATE_PHRASES)


def _is_feishu_login_page(content: str, title: str = "") -> bool:
    """判断是否为飞书登录页（未登录访问飞书内容时的跳转页）。"""
    combined = (content + " " + title).lower()
    return any(p in combined for p in _FEISHU_LOGIN_PHRASES)


def _parse_jina_response(text: str, url: str) -> dict:
    """从 Jina Reader 返回的 markdown 提取 title + content。"""
    lines = text.strip().splitlines()
    title = ""
    body_lines: list[str] = []
    past_meta = False
    for line in lines:
        stripped = line.strip()
        if not past_meta:
            if stripped.startswith("Title:"):
                title = stripped[6:].strip()
                continue
            if stripped.startswith(("URL Source:", "Published Time:")):
                continue
            if stripped.startswith("Markdown Content:"):
                past_meta = True
                continue
        else:
            body_lines.append(line)
    content = "\n".join(body_lines).strip() or text.strip()
    truncated = len(content) > _MAX_CONTENT
    return {
        "platform": "generic",
        "title": title or "（未提取到标题）",
        "author": "",
        "publish_date": "",
        "content": content[:_MAX_CONTENT],
        "word_count": len(content[:_MAX_CONTENT]),
        "url": url,
        **({"truncated": True} if truncated else {}),
    }


class GenericExtractor(ArticleExtractor):
    """兜底抽取器：matches() 始终返回 True，注册在列表最末。
    三级降级：trafilatura → Jina Reader → Playwright（chromium headless）。
    任一级成功即返回，全部失败才报错。
    """

    def matches(self, url: str) -> bool:
        return True

    def extract(self, url: str) -> dict:
        result = self._try_trafilatura(url)
        if result:
            content = result.get("content", "")
            title = result.get("title", "")
            if _is_feishu_login_page(content, title):
                return {
                    "platform": "generic",
                    "error": "该链接需要飞书登录才能访问，无法直接抓取内容。请确认链接是否公开，或直接复制文字内容分享给我。",
                    "url": url,
                }
            if not _is_js_gate(content):
                return result

        result = self._try_jina(url)
        if result:
            return result

        result = self._try_playwright(url)
        if result:
            return result

        return {
            "platform": "generic",
            "error": "所有提取方法均失败（trafilatura/Jina/Playwright）",
            "url": url,
        }

    def _try_trafilatura(self, url: str) -> dict | None:
        try:
            import trafilatura
        except ImportError:
            return None
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            meta = trafilatura.extract_metadata(downloaded)
            content = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            if not content:
                return None
            truncated = len(content) > _MAX_CONTENT
            return {
                "platform": "generic",
                "title": (meta.title if meta and meta.title else "") or "（未提取到标题）",
                "author": (meta.author if meta and meta.author else "") or "",
                "publish_date": (meta.date if meta and meta.date else "") or "",
                "content": content[:_MAX_CONTENT],
                "word_count": len(content[:_MAX_CONTENT]),
                "url": url,
                **({"truncated": True} if truncated else {}),
            }
        except Exception:
            return None

    def _try_jina(self, url: str) -> dict | None:
        try:
            import requests
            resp = requests.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "text/plain", "X-Return-Format": "markdown"},
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            if not text or _is_js_gate(text):
                return None
            return _parse_jina_response(text, url)
        except Exception:
            return None

    def _try_playwright(self, url: str) -> dict | None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="networkidle")
                html = page.content()
                title = page.title()
                browser.close()

            # 优先用 trafilatura 解析渲染后的 HTML
            content: str | None = None
            try:
                import trafilatura
                content = trafilatura.extract(html, include_comments=False, include_tables=True)
            except ImportError:
                pass

            # 降级：纯文本提取
            if not content:
                from html.parser import HTMLParser as _HP

                class _TextParser(_HP):
                    def __init__(self) -> None:
                        super().__init__()
                        self._capture = True
                        self._parts: list[str] = []

                    def handle_starttag(self, tag: str, attrs: object) -> None:
                        self._capture = tag not in ("script", "style", "head", "noscript")

                    def handle_data(self, data: str) -> None:
                        if self._capture and data.strip():
                            self._parts.append(data.strip())

                    def result(self) -> str:
                        return " ".join(self._parts)

                parser = _TextParser()
                parser.feed(html)
                content = parser.result()

            if not content or _is_js_gate(content):
                return None

            truncated = len(content) > _MAX_CONTENT
            return {
                "platform": "generic",
                "title": title or "（未提取到标题）",
                "author": "",
                "publish_date": "",
                "content": content[:_MAX_CONTENT],
                "word_count": len(content[:_MAX_CONTENT]),
                "url": url,
                **({"truncated": True} if truncated else {}),
            }
        except Exception:
            return None
