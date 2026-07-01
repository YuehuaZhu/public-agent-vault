"""雪球（xueqiu.com）内容抽取器 — 支持动态/帖子/文章页面。"""
from __future__ import annotations

import json
import re
from extractors.base import ArticleExtractor

_MAX_CONTENT = 15000

_XQ_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# 匹配 status id：/statuses/123456 或 /<user>/statuses/123456
_STATUS_RE = re.compile(r"xueqiu\.com/(?:[^/]+/)?statuses?/(\d+)")
# 匹配 article id：/p/Z...
_ARTICLE_RE = re.compile(r"xueqiu\.com/p/([A-Za-z0-9_-]+)")


class XueqiuExtractor(ArticleExtractor):
    """
    雪球抽取器，走非官方 JSON API：
    - /statuses/show.json?id=<id>      动态/帖子
    - /statuses/original/show.json?id  （同上备用）
    - HTML fallback 针对文章页
    """

    def matches(self, url: str) -> bool:
        return "xueqiu.com" in url

    def extract(self, url: str) -> dict:
        try:
            # 先尝试 status API
            status_m = _STATUS_RE.search(url)
            if status_m:
                return self._fetch_status(status_m.group(1), url)

            # 再尝试文章页 HTML
            article_m = _ARTICLE_RE.search(url)
            if article_m:
                return self._fetch_article_page(url)

            # 通用 HTML fallback
            return self._fetch_generic(url)
        except Exception as e:
            return {"platform": "xueqiu", "error": f"提取失败: {e}", "url": url}

    # ── Status API ──────────────────────────────────────────────

    def _fetch_status(self, status_id: str, original_url: str) -> dict:
        api_url = f"https://xueqiu.com/statuses/show.json?id={status_id}"
        data = self._api_get(api_url)

        if not data:
            return {"platform": "xueqiu", "error": "雪球 API 返回空响应", "url": original_url}

        # 从 data 里取内容
        status = data.get("status") or data  # 不同版本 API 结构略有差异
        description = self._strip_html(status.get("description") or status.get("text") or "")
        title = status.get("title") or ""
        user = (status.get("user") or {})
        author = user.get("screen_name") or user.get("name") or ""
        created_at = status.get("created_at") or ""
        date = self._parse_date(created_at)

        if not description:
            return {"platform": "xueqiu", "error": "帖子内容为空或需要登录", "url": original_url}

        truncated = len(description) > _MAX_CONTENT
        return {
            "platform": "xueqiu",
            "title": title or f"雪球动态 {status_id}",
            "author": author,
            "publish_date": date,
            "content": description[:_MAX_CONTENT],
            "word_count": len(description),
            "url": original_url,
            **({"truncated": True} if truncated else {}),
        }

    # ── Article page HTML ───────────────────────────────────────

    def _fetch_article_page(self, url: str) -> dict:
        html = self._html_get(url)
        if not html:
            return {"platform": "xueqiu", "error": "文章页面下载失败", "url": url}

        # 尝试从页面内嵌 JSON 中提取
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*;?\s*</script>', html, re.S)
        if m:
            try:
                state = json.loads(m.group(1))
                article = (state.get("article") or {}).get("currentArticle") or {}
                title = article.get("title") or ""
                content = self._strip_html(article.get("text") or article.get("description") or "")
                author = (article.get("user") or {}).get("screen_name") or ""
                date = self._parse_date(article.get("created_at") or "")
                if content:
                    truncated = len(content) > _MAX_CONTENT
                    return {
                        "platform": "xueqiu",
                        "title": title or "（未提取到标题）",
                        "author": author,
                        "publish_date": date,
                        "content": content[:_MAX_CONTENT],
                        "word_count": len(content),
                        "url": url,
                        **({"truncated": True} if truncated else {}),
                    }
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass

        return self._fetch_generic(url)

    # ── 通用 HTML fallback ──────────────────────────────────────

    def _fetch_generic(self, url: str) -> dict:
        try:
            from bs4 import BeautifulSoup
            html = self._html_get(url)
            if not html:
                return {"platform": "xueqiu", "error": "页面下载失败", "url": url}
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            content = soup.get_text(separator="\n", strip=True)
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
        except ImportError:
            return {"platform": "xueqiu", "error": "beautifulsoup4 未安装，无法解析雪球页面", "url": url}

        if not content:
            return {"platform": "xueqiu", "error": "未能提取到内容", "url": url}

        truncated = len(content) > _MAX_CONTENT
        return {
            "platform": "xueqiu",
            "title": title or "（未提取到标题）",
            "author": "",
            "publish_date": "",
            "content": content[:_MAX_CONTENT],
            "word_count": len(content),
            "url": url,
            **({"truncated": True} if truncated else {}),
        }

    # ── HTTP helpers ────────────────────────────────────────────

    def _api_get(self, url: str) -> dict | None:
        headers = {
            "User-Agent": _XQ_UA,
            "Referer": "https://xueqiu.com/",
            "Accept": "application/json, text/plain, */*",
        }
        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            return self._api_get_urllib(url, headers)
        except Exception:
            return None

    def _api_get_urllib(self, url: str, headers: dict) -> dict | None:
        import urllib.request
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except Exception:
            return None

    def _html_get(self, url: str) -> str:
        headers = {"User-Agent": _XQ_UA, "Referer": "https://xueqiu.com/"}
        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.text
        except ImportError:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.read().decode("utf-8", errors="replace")
            except Exception:
                return ""
        except Exception:
            return ""

    # ── 工具方法 ────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """粗略去除 HTML 标签。"""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"&nbsp;", " ", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&gt;", ">", clean)
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"\s{3,}", "\n\n", clean)
        return clean.strip()

    @staticmethod
    def _parse_date(raw: str) -> str:
        """尝试把雪球时间戳（毫秒或字符串）转成 YYYY-MM-DD。"""
        if not raw:
            return ""
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.isdigit()):
            import datetime
            ts = int(raw)
            if ts > 10**12:
                ts //= 1000
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        # 字符串日期，取前 10 位
        return str(raw)[:10]
