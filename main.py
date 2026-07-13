"""
主流程编排脚本。

流程：
  1. 加载 config/keywords.yaml 和 config/companies.yaml
  2. 从各数据源拉取职位：
       - Greenhouse API（美国目标公司）
       - MyCareersFuture API（新加坡）
       - 邮件订阅解析（LinkedIn/Indeed/Glassdoor/Handshake/JobsDB，覆盖US/SG/HK视订阅设置而定）
  3. 按国家/地区分组，用去重记录过滤掉已经发送过的职位
  4. 通过SMTP发送汇总邮件
  5. 更新去重记录

运行方式：python main.py
（GitHub Actions 会在每周二、四自动调用这个脚本）
"""
import os
import yaml

from sources.api.greenhouse_source import fetch_greenhouse_jobs
from sources.api.mycareersfuture_source import fetch_mycareersfuture_jobs
from email_reader import fetch_job_alert_emails
from email_sender import send_summary_email
from dedup_store import load_sent_jobs, save_sent_jobs, filter_new_jobs
from utils import dedup_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(BASE_DIR, "config", "keywords.yaml"), encoding="utf-8") as f:
        keywords_cfg = yaml.safe_load(f)
    with open(os.path.join(BASE_DIR, "config", "companies.yaml"), encoding="utf-8") as f:
        companies_cfg = yaml.safe_load(f)["companies"]
    return keywords_cfg, companies_cfg


def classify_email_job_by_region(job: dict, keywords_cfg: dict) -> str:
    """
    邮件订阅来源（LinkedIn等）不像API那样天然按国家分开，
    这里用 keywords.yaml 里各地区的关键词，尽量猜测这个职位属于哪个地区。
    猜不出来的默认归到 "US"（可以后续根据你的实际使用情况调整这个策略，
    比如改成按 location 字段里的城市名/国家名做更精确匹配）。
    """
    title = job.get("title", "")
    description = job.get("description", "")
    location = job.get("location", "").lower()

    if any(kw in location for kw in ["singapore", "sg", "新加坡"]):
        return "SG"
    if any(kw in location for kw in ["hong kong", "hk", "香港"]):
        return "HK"

    haystack = f"{title} {description}".lower()
    for region in ["SG", "HK"]:
        for kw in keywords_cfg.get(region, {}).get("keywords", []):
            if kw.lower() in haystack:
                return region

    return "US"


def main():
    print("=" * 60)
    print("求职Agent开始运行")
    print("=" * 60)

    keywords_cfg, companies_cfg = load_config()
    max_days_old = keywords_cfg["settings"]["max_days_old"]

    jobs_by_region = {"US": [], "SG": [], "HK": []}

    # ---------- 1. Greenhouse（按公司清单，暂归为US，可按需调整）----------
    print("\n[1/3] 拉取 Greenhouse 职位...")
    gh_jobs = fetch_greenhouse_jobs(
        companies_cfg,
        keywords_cfg["US"]["keywords"],
        keywords_cfg["US"].get("exclude_keywords", []),
        max_days_old,
    )
    jobs_by_region["US"].extend(gh_jobs)

    # ---------- 2. MyCareersFuture（新加坡）----------
    print("\n[2/3] 拉取 MyCareersFuture 职位...")
    mcf_jobs = fetch_mycareersfuture_jobs(
        keywords_cfg["SG"]["keywords"],
        keywords_cfg["SG"].get("exclude_keywords", []),
        max_days_old,
    )
    jobs_by_region["SG"].extend(mcf_jobs)

    # ---------- 3. 邮件订阅（LinkedIn/Indeed/Glassdoor/Handshake/JobsDB）----------
    print("\n[3/3] 解析邮件订阅...")
    email_jobs = fetch_job_alert_emails()
    for job in email_jobs:
        region = classify_email_job_by_region(job, keywords_cfg)
        # 邮件来源没有像API那样提前按关键词过滤，这里补做一次
        region_kw = keywords_cfg.get(region, {})
        title = job.get("title", "")
        description = job.get("description", "")
        haystack = f"{title} {description}".lower()
        exclude_hit = any(ex.lower() in haystack for ex in region_kw.get("exclude_keywords", []))
        keyword_hit = any(kw.lower() in haystack for kw in region_kw.get("keywords", [])) or not region_kw.get("keywords")
        if keyword_hit and not exclude_hit:
            jobs_by_region[region].append(job)

    # ---------- 去重 ----------
    print("\n去重处理中...")
    sent_jobs = load_sent_jobs()
    new_jobs_by_region = {}
    for region, jobs in jobs_by_region.items():
        new_jobs_by_region[region] = filter_new_jobs(jobs, sent_jobs, dedup_key)
        print(f"  {region}: 抓取{len(jobs)}个，去重后新增{len(new_jobs_by_region[region])}个")

    # ---------- 发送邮件 ----------
    total_new = sum(len(v) for v in new_jobs_by_region.values())
    print(f"\n共发现 {total_new} 个新职位，准备发送邮件...")
    send_summary_email(new_jobs_by_region)

    # ---------- 保存去重记录 ----------
    save_sent_jobs(sent_jobs)

    print("\n运行完成。")


if __name__ == "__main__":
    main()
