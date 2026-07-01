"""微信公众号文章抓取器。"""
from __future__ import annotations

import datetime
import html.parser
import re
import urllib.request

from extractors.base import ArticleExtractor

WECHAT_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UQ1A.240205.002) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/122.0.6261.64 Mobile Safari/537.36 "
    "MicroMessenger/8.0.47.2560(0x28002F35) NetType/WIFI Language/zh_CN"
)

# requests + beautifulsoup4 是推荐依赖（见 requirements.txt），
# 未安装时降级到 urllib + 内建 HTML parser，行为正常但提取质量略低。
_HAS_RICH_DEPS = False
try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_RICH_DEPS = True
except ImportError:
    pass


def _fetch_html(url: str) -> str:
    if _HAS_RICH_DEPS:
        resp = requests.get(url, headers={"User-Agent": WECHAT_UA}, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    req = urllib.request.Request(url, headers={"User-Agent": WECHAT_UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset)


def _extract_title(html_text: str, soup=None) -> str:
    if soup:
        h1 = soup.find("h1", class_="rich_media_title")
        if h1:
            return h1.get_text(strip=True)
        og = soup.find("meta", property="og:title")
        if og:
            return (og.get("content") or "").strip()
    m = re.search(r'var\s+msg_title\s*=\s*["\'](.+?)["\']', html_text)
    if m:
        return m.group(1).strip()
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html_text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_author(html_text: str, soup=None) -> str:
    if soup:
        el = soup.find(id="js_name")
        if el:
            return el.get_text(strip=True)
    m = re.search(r'id="js_name"[^>]*>(.*?)</(?:a|strong)', html_text, re.DOTALL)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'var\s+nickname\s*=\s*["\'](.+?)["\']', html_text)
    if m:
        return m.group(1).strip()
    return ""


def _extract_date(html_text: str, soup=None) -> str:
    if soup:
        pt = soup.find(id="publish_time")
        if pt:
            return pt.get_text(strip=True)
    m = re.search(r'id="publish_time"[^>]*>(.*?)</', html_text, re.DOTALL)
    if m:
        d = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if d:
            return d
    m = re.search(r'var\s+(?:ct|create_time)\s*=\s*["\'](\d+)["\']', html_text)
    if m:
        return datetime.datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d")
    m = re.search(r'(\d{4}-\d{2}-\d{2})', html_text[:5000])
    if m:
        return m.group(1)
    return ""


class _ContentExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_content = False
        self._depth = 0
        self._skip_tags = {"script", "style", "img", "svg"}
        self._skip_depth = 0
        self._paragraphs: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if attrs_d.get("id") == "js_content":
            self._in_content = True
            self._depth = 1
            return
        if self._in_content:
            self._depth += 1
            if tag in self._skip_tags:
                self._skip_depth = self._depth
            if tag in ("p", "h1", "h2", "h3", "h4", "blockquote"):
                self._buf = []

    def handle_endtag(self, tag):
        if not self._in_content:
            return
        if self._skip_depth and self._depth <= self._skip_depth:
            self._skip_depth = 0
        if tag in ("p", "h1", "h2", "h3", "h4", "blockquote"):
            text = "".join(self._buf).strip()
            if text and len(text) > 1:
                self._paragraphs.append(text)
            self._buf = []
        self._depth -= 1
        if self._depth <= 0:
            self._in_content = False

    def handle_data(self, data):
        if self._in_content and not self._skip_depth:
            self._buf.append(data)

    def get_content(self) -> str:
        seen: set[str] = set()
        deduped = []
        for p in self._paragraphs:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return "\n\n".join(deduped)


def _extract_content(html_text: str, soup=None) -> str:
    if _HAS_RICH_DEPS and soup:
        js_content = soup.find(id="js_content")
        if js_content:
            for tag in js_content.find_all(["script", "style", "img", "svg"]):
                tag.decompose()
            paragraphs, seen = [], set()
            for el in js_content.find_all(["p", "h1", "h2", "h3", "h4", "blockquote"]):
                text = el.get_text(strip=True)
                if text and len(text) > 1 and text not in seen:
                    seen.add(text)
                    paragraphs.append(text)
            if paragraphs:
                return "\n\n".join(paragraphs)
            return js_content.get_text("\n", strip=True)

    parser = _ContentExtractor()
    parser.feed(html_text)
    content = parser.get_content()
    if content:
        return content
    m = re.search(
        r'id="js_content"[^>]*>(.*?)(?:<div\s+class="rich_media_tool"|$)',
        html_text, re.DOTALL,
    )
    if m:
        raw = re.sub(r'<[^>]+>', '\n', m.group(1))
        lines = [l.strip() for l in raw.split('\n') if l.strip() and len(l.strip()) > 1]
        return "\n\n".join(dict.fromkeys(lines))
    return ""


class WechatExtractor(ArticleExtractor):
    def matches(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def extract(self, url: str, max_chars: int = 15000) -> dict:
        # wappoc_appmsgcaptcha 是微信环境检测跳转页，从 target_url 参数提取真实文章链接
        if "wappoc_appmsgcaptcha" in url:
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(url).query)
            target = qs.get("target_url", [None])[0]
            if target:
                url = unquote(target)
            else:
                return {"platform": "wechat", "error": "无法从跳转链接中提取文章地址，请直接发送文章链接", "url": url}

        try:
            html_text = _fetch_html(url)
        except Exception as e:
            return {"platform": "wechat", "error": f"请求失败: {e}", "url": url}

        soup = None
        if _HAS_RICH_DEPS:
            soup = BeautifulSoup(html_text, "html.parser")  # type: ignore[possibly-undefined]

        title = _extract_title(html_text, soup)
        author = _extract_author(html_text, soup)
        publish_date = _extract_date(html_text, soup)
        content = _extract_content(html_text, soup)

        if not content:
            return {
                "platform": "wechat",
                "error": "未能提取到文章内容，可能文章已被删除或需要关注后查看",
                "url": url,
            }

        content = re.sub(r"\n{3,}", "\n\n", content)
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars] + "\n\n...（正文过长，已截断）"

        result = {
            "platform": "wechat",
            "title": title or "（未提取到标题）",
            "author": author or "（未知公众号）",
            "publish_date": publish_date or "（未知日期）",
            "content": content,
            "word_count": len(content),
            "url": url,
            "image_count": 0,
        }
        if truncated:
            result["truncated"] = True
        return result
