from __future__ import annotations
from abc import ABC, abstractmethod


class ArticleExtractor(ABC):
    """所有平台抽取器的抽象基类。"""

    @abstractmethod
    def matches(self, url: str) -> bool:
        """判断本抽取器是否能处理此 URL。"""

    @abstractmethod
    def extract(self, url: str) -> dict:
        """
        抓取并解析文章，返回统一 schema dict：
        {platform, title, author, publish_date, content, word_count, url, image_count, error}
        成功时 error 为 None 或不含该键；失败时至少含 error 和 url。
        """
