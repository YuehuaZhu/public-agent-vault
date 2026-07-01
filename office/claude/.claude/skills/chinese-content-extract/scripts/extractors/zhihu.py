"""知乎文章/回答抽取器 — 支持专栏文章和问题回答页面。"""
from __future__ import annotations

import re
from extractors.base import ArticleExtractor

_MAX_CONTENT = 15000

_ZHIHU_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

_ZHIHU_HEADERS = {
    "User-Agent": _ZHIHU_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.zhihu.com/",
}

# 匹配知乎专栏文章（/p/数字）和问题回答页（/question/数字）
_ZHIHU_RE = re.compile(r"zhihu\.com/(p/\d+|question/\d+)")


class ZhihuExtractor(ArticleExtractor):
    """
    知乎抽取器：
    - zhihu.com/p/<id>          专栏文章
    - zhihu.com/question/<id>   问题页（抓取第一个高赞回答）
    大部分内容无需登录，用 Chrome UA 即可访问。
    """

    def matches(self, url: str) -> bool:
        return bool(_ZHIHU_RE.search(url))

    def extract(self, url: str) -> dict:
        try:
            import requests
            from bs4 import BeautifulSoup
            _rich = True
        except ImportError:
            _rich = False

        try:
            if _rich:
                return self._extract_rich(url)
            return self._extract_fallback(url)
        except Exception as e:
            return {"platform": "zhihu", "error": f"请求失败: {e}", "url": url}

    # ── rich path (requests + bs4) ─────────────────────────────

    def _extract_rich(self, url: str) -> dict:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=_ZHIHU_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        if "/p/" in url:
            return self._parse_article(soup, url)
        return self._parse_question(soup, url)

    def _parse_article(self, soup, url: str) -> dict:
        title = self._get_title(soup)
        author = self._get_author_article(soup)
        date = self._get_date(soup)
        content = self._get_content_article(soup)

        if not content:
            return {"platform": "zhihu", "error": "未能提取到文章正文（可能需要登录）", "url": url}

        truncated = len(content) > _MAX_CONTENT
        return {
            "platform": "zhihu",
            "title": title or "（未提取到标题）",
            "author": author or "",
            "publish_date": date or "",
            "content": content[:_MAX_CONTENT],
            "word_count": len(content),
            "url": url,
            **({"truncated": True} if truncated else {}),
        }

    def _parse_question(self, soup, url: str) -> dict:
        # 问题标题
        h1 = soup.find("h1", class_=re.compile(r"QuestionHeader-title"))
        title = h1.get_text(strip=True) if h1 else ""

        # 第一个回答的内容
        answer_div = soup.find("div", class_=re.compile(r"RichContent-inner"))
        if not answer_div:
            # fallback：找任何 .RichText 容器
            answer_div = soup.find("div", class_=re.compile(r"RichText"))

        content = answer_div.get_text(separator="\n", strip=True) if answer_div else ""
        if not content:
            return {"platform": "zhihu", "error": "未能提取到回答内容（可能需要登录或页面为空）", "url": url}

        truncated = len(content) > _MAX_CONTENT
        return {
            "platform": "zhihu",
            "title": title or "（未提取到标题）",
            "author": "",
            "publish_date": "",
            "content": content[:_MAX_CONTENT],
            "word_count": len(content),
            "url": url,
            **({"truncated": True} if truncated else {}),
        }

    # ── 字段解析辅助 ───────────────────────────────────────────

    @staticmethod
    def _get_title(soup) -> str:
        for selector in [
            ("h1", {"class": re.compile(r"Post-Title|ArticleHeader-title")}),
            ("h1", {}),
        ]:
            tag = soup.find(*selector)
            if tag:
                return tag.get_text(strip=True)
        # og:title fallback
        og = soup.find("meta", property="og:title")
        return og["content"].strip() if og and og.get("content") else ""

    @staticmethod
    def _get_author_article(soup) -> str:
        tag = soup.find("a", class_=re.compile(r"UserLink-link|AuthorInfo-name"))
        if tag:
            return tag.get_text(strip=True)
        tag = soup.find("meta", {"name": "author"})
        return tag["content"].strip() if tag and tag.get("content") else ""

    @staticmethod
    def _get_date(soup) -> str:
        # og:article:published_time
        og = soup.find("meta", property="article:published_time")
        if og and og.get("content"):
            return og["content"][:10]
        # time 标签
        t = soup.find("time")
        if t and t.get("datetime"):
            return t["datetime"][:10]
        return ""

    @staticmethod
    def _get_content_article(soup) -> str:
        div = soup.find("div", class_=re.compile(r"Post-RichTextContainer|RichText"))
        if not div:
            return ""
        # 删掉 script/style
        for tag in div.find_all(["script", "style"]):
            tag.decompose()
        return div.get_text(separator="\n", strip=True)

    # ── fallback path (urllib) ─────────────────────────────────

    def _extract_fallback(self, url: str) -> dict:
        import urllib.request
        req = urllib.request.Request(url, headers=_ZHIHU_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")

        title = self._re_extract(html, r'<title>([^<]+)</title>')
        content_m = re.search(r'"content":"(.*?)"(?:,"voteCount"|,"updatedTime")', html, re.S)
        content = content_m.group(1).replace("\\n", "\n").replace('\\"', '"') if content_m else ""

        if not content:
            return {"platform": "zhihu", "error": "未能提取到内容（降级模式）", "url": url}

        truncated = len(content) > _MAX_CONTENT
        return {
            "platform": "zhihu",
            "title": title or "（未提取到标题）",
            "author": "",
            "publish_date": "",
            "content": content[:_MAX_CONTENT],
            "word_count": len(content),
            "url": url,
            **({"truncated": True} if truncated else {}),
        }

    @staticmethod
    def _re_extract(html: str, pattern: str) -> str:
        m = re.search(pattern, html)
        return m.group(1).strip() if m else ""
