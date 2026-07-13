"""
IMAP邮件读取模块。

登录到你专门用来接收各网站 Job Alert 的邮箱，拉取"上次运行之后
新收到的"未读邮件，按发件人分发给对应网站的parser去解析。

环境变量（在GitHub Secrets里配置）：
  IMAP_HOST      例如 imap.gmail.com
  IMAP_PORT      例如 993
  IMAP_USER      专用邮箱地址
  IMAP_PASSWORD  应用专用密码（不是邮箱登录密码！）
"""
import imaplib
import email
import os
from email.header import decode_header

from sources.email_parsers.linkedin_parser import LinkedInParser
from sources.email_parsers.indeed_parser import IndeedParser
from sources.email_parsers.glassdoor_parser import GlassdoorParser
from sources.email_parsers.handshake_parser import HandshakeParser
from sources.email_parsers.jobsdb_parser import JobsDBParser

PARSERS = [LinkedInParser(), IndeedParser(), GlassdoorParser(), HandshakeParser(), JobsDBParser()]


def _decode_mime(value: str) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="ignore")
        else:
            result += part
    return result


def _get_html_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        return ""
    else:
        if msg.get_content_type() == "text/html":
            charset = msg.get_content_charset() or "utf-8"
            return msg.get_payload(decode=True).decode(charset, errors="ignore")
        return ""


def _match_parser(from_addr: str):
    from_addr_lower = from_addr.lower()
    for parser in PARSERS:
        for sender_pattern in parser.sender_match:
            if sender_pattern.lower() in from_addr_lower:
                return parser
    return None


def fetch_job_alert_emails() -> list:
    """
    连接IMAP邮箱，读取未读邮件，用对应parser解析，返回统一格式的职位列表。
    处理完的邮件会被标记为已读（不会删除），避免下次重复处理。
    """
    host = os.environ.get("IMAP_HOST")
    port = int(os.environ.get("IMAP_PORT", "993"))
    user = os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")

    if not all([host, user, password]):
        print("[EmailReader] 未配置IMAP相关环境变量，跳过邮件订阅数据源。")
        return []

    all_jobs = []

    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        conn.select("INBOX")

        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            print("[EmailReader] 搜索未读邮件失败。")
            return []

        mail_ids = data[0].split()
        print(f"[EmailReader] 发现 {len(mail_ids)} 封未读邮件。")

        for mail_id in mail_ids:
            status, msg_data = conn.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            from_addr = _decode_mime(msg.get("From", ""))
            received_at = msg.get("Date", "")

            parser = _match_parser(from_addr)
            if parser is None:
                # 不是我们关心的5个网站发来的邮件，跳过，且不标记已读，
                # 避免影响你邮箱里其他邮件的正常已读/未读状态
                continue

            html_body = _get_html_body(msg)
            if not html_body:
                print(f"[EmailReader] {parser.source_name} 邮件没有HTML正文，跳过：{from_addr}")
                continue

            try:
                jobs = parser.parse(html_body, received_at)
                print(f"[EmailReader] {parser.source_name} 邮件解析出 {len(jobs)} 个职位")
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[EmailReader] {parser.source_name} 解析失败: {e}")

            # 标记为已读，避免下次重复处理
            conn.store(mail_id, "+FLAGS", "\\Seen")

        conn.close()
        conn.logout()

    except imaplib.IMAP4.error as e:
        print(f"[EmailReader] IMAP登录/操作失败，请检查IMAP_USER/IMAP_PASSWORD是否正确（Gmail需用应用专用密码）: {e}")
    except Exception as e:
        print(f"[EmailReader] 未知错误: {e}")

    return all_jobs
