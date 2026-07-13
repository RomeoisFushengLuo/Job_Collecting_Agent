"""
去重记录管理：记住哪些职位已经推送过，避免下次运行重复发送。

存储在 data/sent_jobs.json，是一个简单的 {dedup_key: 首次发送日期} 字典。
为了避免文件无限膨胀，超过 RETENTION_DAYS 天没再出现的记录会被清理掉
（因为职位早已过期，没必要一直占着去重名单）。
"""
import json
import os
from datetime import datetime, timedelta

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sent_jobs.json")
RETENTION_DAYS = 30


def load_sent_jobs() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[DedupStore] 读取去重记录失败，将视为空记录重新开始: {e}")
        return {}


def save_sent_jobs(sent_jobs: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    # 清理过期记录
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    cleaned = {k: v for k, v in sent_jobs.items() if v >= cutoff}

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"[DedupStore] 保存去重记录，共 {len(cleaned)} 条（清理前 {len(sent_jobs)} 条）")


def filter_new_jobs(jobs: list, sent_jobs: dict, key_fn) -> list:
    """返回jobs中还没发送过的部分，同时把新职位登记进sent_jobs（原地修改）"""
    today = datetime.now().strftime("%Y-%m-%d")
    new_jobs = []
    for job in jobs:
        key = key_fn(job)
        if key not in sent_jobs:
            sent_jobs[key] = today
            new_jobs.append(job)
    return new_jobs
