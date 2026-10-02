"""Outbound email over SMTP (works with Brevo, Gmail, or any relay). Preview-only without credentials."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .. import config
from ..models import SendResult


def send(to: str, subject: str, body: str) -> SendResult:
    to = (to or "").strip()
    if not config.valid_email(to):
        return SendResult(status="failed", detail="Recipient email address is missing or invalid.", recipient=to)
    if not config.email_available():
        return SendResult(
            status="preview",
            detail="Email credentials are not configured, so nothing was sent. This is a preview only.",
            recipient=to,
        )

    msg = EmailMessage()
    msg["From"] = config.get("SMTP_FROM")
    msg["To"] = to
    # Header values must stay on one line.
    msg["Subject"] = " ".join(subject.split())
    msg.set_content(body)

    try:
        with smtplib.SMTP(config.get("SMTP_HOST"), int(config.get("SMTP_PORT", "587")), timeout=20) as smtp:
            smtp.starttls()
            smtp.login(config.get("SMTP_USER"), config.get("SMTP_PASSWORD"))
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        return SendResult(status="failed", detail=f"Email was not sent: {type(exc).__name__}", recipient=to)
    return SendResult(status="sent", detail="Email accepted by the mail server.", recipient=to)
