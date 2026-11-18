"""E-mail via SMTP. Without SMTP_HOST, messages are saved to data/outbox so you can preview them."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from sqlalchemy.orm import Session

from .config import get_config
from .models import NotificationLog
from .timeutil import utcnow

log = logging.getLogger("nudge.mail")
OUTBOX_KEEP = 30


def configured() -> bool:
    return bool(get_config().smtp_host)


def outbox_dir():
    path = get_config().data_dir / "outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def send(db: Session, kind: str, to: str, subject: str, html: str, text: str) -> bool:
    cfg = get_config()
    entry = NotificationLog(kind=kind, channel="email", title=subject[:200], body=text[:2000], at=utcnow())
    db.add(entry)
    if not to:
        entry.error = "no recipient set"
        db.flush()
        return False
    msg = EmailMessage()
    sender = cfg.smtp_from or cfg.smtp_user or "nudge@localhost"
    msg["From"] = formataddr(("Nudge", sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else "nudge.local")
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    if not configured():
        stamp = utcnow().strftime("%Y%m%d-%H%M%S")
        (outbox_dir() / f"{stamp}-{kind}.html").write_text(html)
        (outbox_dir() / f"{stamp}-{kind}.eml").write_bytes(bytes(msg))
        files = sorted(outbox_dir().glob("*"), key=lambda p: p.name)
        for old in files[: max(0, len(files) - 2 * OUTBOX_KEEP)]:
            old.unlink(missing_ok=True)
        entry.error = "saved to outbox (SMTP not set up)"
        db.flush()
        return False

    try:
        if cfg.smtp_security == "ssl":
            server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ssl.create_default_context(), timeout=20)
        else:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20)
            if cfg.smtp_security == "starttls":
                server.starttls(context=ssl.create_default_context())
        with server:
            if cfg.smtp_user:
                server.login(cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)
        entry.delivered = 1
        db.flush()
        return True
    except (smtplib.SMTPException, OSError) as e:
        entry.error = str(e)[:500]
        log.warning("E-mail failed: %s", e)
        db.flush()
        return False


def latest_outbox() -> list[dict]:
    if not get_config().data_dir.joinpath("outbox").exists():
        return []
    files = sorted(outbox_dir().glob("*.html"), key=lambda p: p.name, reverse=True)[:10]
    return [{"name": f.name, "size": f.stat().st_size} for f in files]
