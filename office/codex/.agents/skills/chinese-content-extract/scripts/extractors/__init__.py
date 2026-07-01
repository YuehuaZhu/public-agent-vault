from __future__ import annotations
from extractors.base import ArticleExtractor
from extractors.wechat import WechatExtractor
from extractors.zhihu import ZhihuExtractor
from extractors.xueqiu import XueqiuExtractor
from extractors.xiaohongshu import XiaohongshuExtractor
from extractors.generic import GenericExtractor

# 顺序即优先级：专用 extractor 在前，generic fallback 在最后
EXTRACTORS: list[ArticleExtractor] = [
    WechatExtractor(),
    ZhihuExtractor(),
    XueqiuExtractor(),
    XiaohongshuExtractor(),     # 小红书：xhs库(Tier1) → Playwright(Tier2) → 提示(Tier3)
    GenericExtractor(),         # 兜底：任意 URL，依赖 trafilatura
]


def find_extractor(url: str) -> ArticleExtractor | None:
    for e in EXTRACTORS:
        if e.matches(url):
            return e
    return None
