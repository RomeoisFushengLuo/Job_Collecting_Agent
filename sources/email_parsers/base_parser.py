"""
邮件解析器基类。

每个网站的 Job Alert 邮件 HTML 结构不同，所以每个网站需要一个独立的
解析器。这个基类只提供共享的工具方法；具体的"怎么从HTML里挖出职位
标题/公司/链接"的逻辑，每个子类各写各的。

⚠️ 当前各解析器（linkedin/indeed/glassdoor/handshake/jobsdb_parser.py）
都是【骨架 + 尽力而为的通用启发式规则】，不是根据真实邮件样本精确
调试过的版本。请你订阅生效、收到第一封真实的Job Alert邮件后，把邮件
转发或者截图/导出HTML源码发给我，我会针对性把对应的parser改准。
在此之前，这几个解析器可能解析不全、漏字段，请不要完全依赖它们。
"""
from bs4 import BeautifulSoup


class BaseEmailParser:
    source_name = "Unknown"
    # 用于 email_reader.py 匹配这个解析器该处理哪些邮件（按发件人地址关键字判断）
    sender_match = []

    def parse(self, raw_html: str, received_at: str) -> list:
        """
        解析一封邮件的HTML正文，返回职位列表（可能包含0到多个职位，
        因为很多网站的Job Alert一封邮件里会打包好几个推荐职位）。
        子类必须实现这个方法。
        """
        raise NotImplementedError

    @staticmethod
    def _soup(raw_html: str) -> BeautifulSoup:
        return BeautifulSoup(raw_html or "", "html.parser")

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split()).strip()

    @staticmethod
    def _first_link_in(tag) -> str:
        """从一个HTML片段里找第一个看起来像职位详情页的<a>链接"""
        if tag is None:
            return ""
        a = tag.find("a", href=True)
        return a["href"] if a else ""
