"""
LinkedIn "Job Alert" 邮件解析器。

常见发件人地址（需你实际收到邮件后核实并按需调整 sender_match）：
  jobalerts-noreply@linkedin.com
  jobs-noreply@linkedin.com

⚠️ 骨架版本，尚未用真实邮件样本校准，见 base_parser.py 顶部说明。
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sources.email_parsers.base_parser import BaseEmailParser
from utils import strip_html


class LinkedInParser(BaseEmailParser):
    source_name = "LinkedIn"
    sender_match = ["jobalerts-noreply@linkedin.com", "jobs-noreply@linkedin.com"]

    def parse(self, raw_html: str, received_at: str) -> list:
        soup = self._soup(raw_html)
        jobs = []

        # LinkedIn 的职位提醒邮件通常每个职位是一个独立的表格/区块，
        # 标题是一个指向 linkedin.com/jobs/view/... 的链接。
        candidate_links = soup.find_all("a", href=True)
        seen = set()

        for a in candidate_links:
            href = a["href"]
            if "linkedin.com/jobs/view" not in href and "/comm/jobs/view" not in href:
                continue

            title = self._clean_text(a.get_text())
            if not title or href in seen:
                continue
            seen.add(href)

            # 尝试往上找父级容器，从里面挖公司名和地点（结构因邮件模板而异，
            # 这里做了几层try，找不到就留空，好过直接解析失败）
            company = ""
            location = ""
            container = a.find_parent("table") or a.find_parent("td") or a.parent
            if container:
                text_block = self._clean_text(container.get_text(separator=" | "))
                parts = [p.strip() for p in text_block.split("|") if p.strip()]
                # 通常紧跟标题后面一两段文字是 公司名 / 地点
                if len(parts) >= 2:
                    company = parts[1] if parts[0] == title else parts[0]
                if len(parts) >= 3:
                    location = parts[2]

            jobs.append({
                "source": self.source_name,
                "company": company,
                "title": title,
                "location": location,
                "posted_time": received_at,  # 邮件里通常不直接给发布时间，用收信时间近似
                "description": "",  # LinkedIn提醒邮件一般不含完整职位描述，只有摘要/无描述
                "link": href.split("?")[0],
            })

        return jobs
