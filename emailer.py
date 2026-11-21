"""Sends league emails through the Gmail bot account."""
import os
import smtplib
from email.message import EmailMessage

from flask import current_app

BOT_USER = "bramptonsquashbot@gmail.com"


def _one_line(value):
    return " ".join(str(value).split())


def send_email(subject, body, to, reply_to=None):
    """Send a plain-text email. Returns True on success, False on failure.

    When running locally (no live database) nothing is actually sent: the
    message is printed to the console so testing never emails real people.
    Set SEND_EMAIL_IN_DEV=1 to override that.
    """
    if not current_app.config["IS_PROD"] and not os.getenv("SEND_EMAIL_IN_DEV"):
        current_app.logger.warning(
            "[DEV - email not sent] To: %s | Reply-To: %s | Subject: %s\n%s", to, reply_to, subject, body
        )
        return True

    password = os.getenv("bot_password")
    if not password:
        current_app.logger.error("Email not sent: bot_password is not set")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = _one_line(subject)
        msg["From"] = BOT_USER
        msg["To"] = _one_line(to)
        if reply_to:
            msg["Reply-To"] = _one_line(reply_to)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(BOT_USER, password)
            server.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception("Email send failed (to=%s)", to)
        return False
