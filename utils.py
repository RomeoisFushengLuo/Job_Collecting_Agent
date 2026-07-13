"""
共享工具函数：关键词匹配、HTML清洗、日期处理等。
"""
import re
import html
from datetime import datetime, timezone, timedelta


def strip_html(raw_html: str, max_length: int = 1200) -> str:
    """去除HTML标签，返回纯文本描述，并截断到合理长度用于邮件展示。"""
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "…"
    return text


def matches_keywords(title: str, description: str, keywords: list, exclude_keywords: list = None) -> bool:
    """
    判断职位是否命中关键词。
    - keywords 是"或"关系，任意命中一个即可
    - exclude_keywords 命中即排除，优先级最高
    """
    exclude_keywords = exclude_keywords or []
    haystack = f"{title} {description}".lower()

    for ex in exclude_keywords:
        if ex.lower() in haystack:
            return False

    if not keywords:
        # 没配置关键词时，默认不过滤（全部收录）
        return True

    for kw in keywords:
        if kw.lower() in haystack:
            return True

    return False


def is_recent(date_str: str, max_days_old: int) -> bool:
    """
    判断给定的ISO格式日期字符串是否在 max_days_old 天以内。
    解析失败时默认视为"符合条件"，避免因为日期格式差异漏掉职位。
    """
    if not date_str:
        return True
    try:
        # 兼容形如 2026-07-08T10:30:00-05:00 或 2026-07-08T10:30:00Z 的格式
        cleaned = date_str.replace("Z", "+00:00")
        posted = datetime.fromisoformat(cleaned)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - posted) <= timedelta(days=max_days_old)
    except Exception:
        return True


def clean_env(value: str) -> str:
    """
    清理环境变量里可能混入的空白字符——包括从网页复制粘贴时常见的
    "不间断空格"(\\xa0)之类肉眼看不出来但会导致 UnicodeEncodeError /
    登录失败的字符。凡是host/port/账号/密码这类值都不应该包含任何
    空白，所以直接把所有空白字符全部去掉，而不是只trim首尾。
    """
    if value is None:
        return value
    return re.sub(r"\s+", "", value)


def dedup_key(job: dict) -> str:
    """生成职位的去重key，优先用link，没有link时退化用 source+company+title。"""
    if job.get("link"):
        return job["link"].strip().split("?")[0]  # 去掉URL的query参数避免同一职位因追踪参数不同被判定为不同
    return f"{job.get('source','')}_{job.get('company','')}_{job.get('title','')}"
