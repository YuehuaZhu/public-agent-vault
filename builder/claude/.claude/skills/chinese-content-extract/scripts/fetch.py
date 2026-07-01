#!/usr/bin/env python3
"""中文内容抽取 CLI 入口。用法: python fetch.py <url>  → 打印结构化 JSON。"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractors import find_extractor


def fetch(url: str) -> dict:
    if not url or not url.strip():
        return {"error": "URL 为空", "url": url}
    ex = find_extractor(url)
    if ex is None:
        return {"error": "不支持的链接平台（支持：微信公众号 / 知乎 / 雪球 + 通用网页 fallback）", "url": url}
    return ex.extract(url)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "用法: python fetch.py <url>"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(fetch(sys.argv[1]), ensure_ascii=False, indent=2))
