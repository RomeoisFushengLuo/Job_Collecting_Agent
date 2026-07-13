"""
Glassdoor "Job Alert" 邮件解析器。

常见发件人地址（需你实际收到邮件后核实并按需调整 sender_match）：
  noreply@glassdoor.com

⚠️ 骨架版本，尚未用真实邮件样本校准，见 base_parser.py 顶部说明。
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sources.email_parsers.base_parser import BaseEmailParser


class GlassdoorParser(BaseEmailParser):
    source_name = "Glassdoor"
    sender_match = ["noreply@glassdoor.com"]

    def parse(self, raw_html: str, received_at: str) -> list:
        soup = self._soup(raw_html)
        jobs = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "glassdoor.com/job-listing" not in href and "glassdoor.com/partner/jobListing" not in href:
                continue

            title = self._clean_text(a.get_text())
            if not title or href in seen:
                continue
            seen.add(href)

            company = ""
            location = ""
            container = a.find_parent("table") or a.find_parent("td") or a.parent
            if container:
                text_block = self._clean_text(container.get_text(separator=" | "))
                parts = [p.strip() for p in text_block.split("|") if p.strip() and p.strip() != title]
                if len(parts) >= 1:
                    company = parts[0]
                if len(parts) >= 2:
                    location = parts[1]

            jobs.append({
                "source": self.source_name,
                "company": company,
                "title": title,
                "location": location,
                "posted_time": received_at,
                "description": "",
                "link": href.split("?")[0],
            })

        return jobs
