"""
MyCareersFuture（新加坡政府招聘平台）数据源。

⚠️ 重要说明：
这不是一个官方文档化、承诺稳定的第三方API，而是 MyCareersFuture
网站前端自己在用的内部接口，社区长期以来公开在用（无需登录/认证）。
现阶段（2026年7月）请求地址与参数如下，但官方随时可能调整，
如果某天突然全部返回失败，请检查该接口是否已变更（可以打开
mycareersfuture.gov.sg 网站，用浏览器开发者工具的Network面板
观察搜索请求实际发到了哪个地址、带什么参数，然后回来更新这里的
BASE_URL和参数）。

已知接口：POST https://api.mycareersfuture.gov.sg/v2/search
"""
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import strip_html, matches_keywords, is_recent

MCF_SEARCH_URL = "https://api.mycareersfuture.gov.sg/v2/search"
REQUEST_TIMEOUT = 15
PAGE_SIZE = 100


def fetch_mycareersfuture_jobs(keywords: list, exclude_keywords: list, max_days_old: int, max_pages: int = 3) -> list:
    """
    对 keywords 中的每个关键词分别发起搜索请求（该API本身按单个搜索词查询更可靠），
    合并结果后再用 matches_keywords 统一做一次关键词+排除词校验去除误判。
    """
    results = []
    seen_urls = set()

    if not keywords:
        return results

    for kw in keywords:
        for page in range(max_pages):
            payload = {
                "search": kw,
                "page": page,
                "limit": PAGE_SIZE,
                "sortBy": ["new_posting_date"],
            }
            try:
                resp = requests.post(MCF_SEARCH_URL, json=payload, timeout=REQUEST_TIMEOUT,
                                      headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.RequestException as e:
                print(f"[MyCareersFuture] 关键词'{kw}'第{page}页请求失败: {e}")
                break
            except ValueError as e:
                print(f"[MyCareersFuture] 关键词'{kw}'第{page}页JSON解析失败: {e}")
                break

            jobs = data.get("results", [])
            if not jobs:
                break

            for job in jobs:
                title = job.get("title", "")
                description = strip_html(job.get("description", ""))
                uuid = job.get("uuid", "")
                link = f"https://www.mycareersfuture.gov.sg/job/{job.get('metadata', {}).get('jobDetailsUrl', uuid)}" if uuid else ""

                if not link or link in seen_urls:
                    continue

                if not matches_keywords(title, description, keywords, exclude_keywords):
                    continue

                posted_time = job.get("metadata", {}).get("newPostingDate", "") or job.get("metadata", {}).get("originalPostingDate", "")
                if not is_recent(posted_time, max_days_old):
                    continue

                company = job.get("postedCompany", {}).get("name", "")

                results.append({
                    "source": "MyCareersFuture",
                    "company": company,
                    "title": title,
                    "location": "Singapore",
                    "posted_time": posted_time,
                    "description": description,
                    "link": link,
                })
                seen_urls.add(link)

            if len(jobs) < PAGE_SIZE:
                break  # 已经是最后一页

    print(f"[MyCareersFuture] 共命中 {len(results)} 个职位")
    return results


if __name__ == "__main__":
    import yaml

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(base_dir, "config", "keywords.yaml"), encoding="utf-8") as f:
        kw_cfg = yaml.safe_load(f)

    jobs = fetch_mycareersfuture_jobs(
        kw_cfg["SG"]["keywords"],
        kw_cfg["SG"].get("exclude_keywords", []),
        kw_cfg["settings"]["max_days_old"],
    )
    for j in jobs:
        print(j["title"], "|", j["company"], "|", j["link"])
