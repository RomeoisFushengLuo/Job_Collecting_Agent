"""
Greenhouse Job Board API 数据源。

官方公开API，GET请求无需认证：
  https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

注意：这是"按公司查询"，不是全网搜索。需要在 config/companies.yaml
里配置你想追踪的公司清单（board_token）。
"""
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils import strip_html, matches_keywords, is_recent

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"
REQUEST_TIMEOUT = 15


def fetch_greenhouse_jobs(companies: list, keywords: list, exclude_keywords: list, max_days_old: int) -> list:
    """
    companies: [{"name": "Airbnb", "board_token": "airbnb"}, ...]
    keywords / exclude_keywords: 来自 keywords.yaml 对应国家/地区的配置
    返回统一格式的职位列表
    """
    results = []

    for company in companies:
        token = company.get("board_token")
        name = company.get("name", token)
        if not token:
            continue

        url = f"{GREENHOUSE_API_BASE}/{token}/jobs?content=true"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[Greenhouse] 拉取 {name} ({token}) 失败: {e}")
            continue
        except ValueError as e:
            print(f"[Greenhouse] 解析 {name} ({token}) 返回的JSON失败: {e}")
            continue

        jobs = data.get("jobs", [])
        for job in jobs:
            title = job.get("title", "")
            raw_content = job.get("content", "")
            description = strip_html(raw_content)
            updated_at = job.get("updated_at", "")

            if not matches_keywords(title, description, keywords, exclude_keywords):
                continue
            if not is_recent(updated_at, max_days_old):
                continue

            location = ""
            if isinstance(job.get("location"), dict):
                location = job["location"].get("name", "")

            results.append({
                "source": "Greenhouse",
                "company": name,
                "title": title,
                "location": location,
                "posted_time": updated_at,
                "description": description,
                "link": job.get("absolute_url", ""),
            })

        print(f"[Greenhouse] {name}: 共{len(jobs)}个职位，命中关键词{sum(1 for j in results if j['company']==name)}个")

    return results


if __name__ == "__main__":
    # 简单本地测试入口：python sources/api/greenhouse_source.py
    import yaml

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(base_dir, "config", "companies.yaml"), encoding="utf-8") as f:
        companies_cfg = yaml.safe_load(f)["companies"]
    with open(os.path.join(base_dir, "config", "keywords.yaml"), encoding="utf-8") as f:
        kw_cfg = yaml.safe_load(f)

    jobs = fetch_greenhouse_jobs(
        companies_cfg,
        kw_cfg["US"]["keywords"],
        kw_cfg["US"].get("exclude_keywords", []),
        kw_cfg["settings"]["max_days_old"],
    )
    for j in jobs:
        print(j["title"], "|", j["company"], "|", j["link"])
