"""
SMTP邮件发送模块：把汇总好的职位列表格式化成HTML邮件发给你。

环境变量（在GitHub Secrets里配置）：
  SMTP_HOST        例如 smtp.gmail.com
  SMTP_PORT        例如 587
  SMTP_USER        发件邮箱地址
  SMTP_PASSWORD    应用专用密码
  RECIPIENT_EMAIL  你接收汇总邮件的地址（可以就是你日常邮箱）
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _build_html(jobs_by_region: dict) -> str:
    total = sum(len(v) for v in jobs_by_region.values())
    today = datetime.now().strftime("%Y-%m-%d")

    html = f"""
    <html>
    <body style="font-family: -apple-system, Segoe UI, Arial, sans-serif; color:#1a1a1a; max-width:800px; margin:0 auto;">
      <h2 style="border-bottom:2px solid #2563eb; padding-bottom:8px;">
        求职信息汇总 · {today} · 共 {total} 个新职位
      </h2>
    """

    region_names = {"US": "🇺🇸 美国", "SG": "🇸🇬 新加坡", "HK": "🇭🇰 香港"}

    for region, jobs in jobs_by_region.items():
        if not jobs:
            continue
        html += f'<h3 style="color:#2563eb; margin-top:28px;">{region_names.get(region, region)}（{len(jobs)}个）</h3>'
        html += '<table style="width:100%; border-collapse:collapse;">'
        for job in jobs:
            title = job.get("title", "(无标题)")
            company = job.get("company", "")
            location = job.get("location", "")
            posted_time = job.get("posted_time", "")
            description = job.get("description", "")
            link = job.get("link", "#")
            source = job.get("source", "")

            html += f"""
            <tr>
              <td style="padding:14px 0; border-bottom:1px solid #e5e7eb;">
                <div style="font-size:16px; font-weight:600;">
                  <a href="{link}" style="color:#111827; text-decoration:none;">{title}</a>
                </div>
                <div style="font-size:13px; color:#6b7280; margin-top:4px;">
                  {company}{" · " + location if location else ""} · 来源：{source}
                  {" · 发布/更新时间：" + posted_time if posted_time else ""}
                </div>
                {f'<div style="font-size:13px; color:#374151; margin-top:8px; line-height:1.5;">{description[:300]}{"..." if len(description) > 300 else ""}</div>' if description else ""}
                <div style="margin-top:6px;">
                  <a href="{link}" style="font-size:13px; color:#2563eb;">查看职位详情 →</a>
                </div>
              </td>
            </tr>
            """
        html += "</table>"

    if total == 0:
        html += '<p style="color:#6b7280;">这次没有发现新的匹配职位。</p>'

    html += """
    </body>
    </html>
    """
    return html


def send_summary_email(jobs_by_region: dict) -> bool:
    """
    jobs_by_region: {"US": [...], "SG": [...], "HK": [...]}
    发送成功返回True，失败返回False（不抛异常，避免中断整个流程导致
    去重记录状态不一致）。
    """
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not all([host, user, password, recipient]):
        print("[EmailSender] SMTP相关环境变量未配置完整，无法发送邮件。")
        return False

    total = sum(len(v) for v in jobs_by_region.values())
    today = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"求职信息汇总 {today}（{total}个新职位）"
    msg["From"] = user
    msg["To"] = recipient

    html_content = _build_html(jobs_by_region)
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [recipient], msg.as_string())
        print(f"[EmailSender] 邮件已发送至 {recipient}，共{total}个职位。")
        return True
    except smtplib.SMTPException as e:
        print(f"[EmailSender] 发送失败: {e}")
        return False
