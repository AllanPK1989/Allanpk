"""Send email through Gmail SMTP (STARTTLS, app password)."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from ..config import get_settings

log = logging.getLogger(__name__)


def send(subject: str, html: str, text: str, *, to: str | None = None) -> bool:
    s = get_settings()
    if not s.email_enabled:
        log.info("email not configured; skipping '%s'", subject)
        return False
    recipient = to or s.email_to
    msg = EmailMessage()
    msg["Subject"] = subject[:200]
    msg["From"] = formataddr((s.app_name, s.gmail_user))
    msg["To"] = recipient
    msg["Message-ID"] = make_msgid(domain=s.gmail_user.split("@")[-1] or None)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(s.gmail_user, s.gmail_app_password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        log.error("email send failed: %s", e)
        return False
    return True
