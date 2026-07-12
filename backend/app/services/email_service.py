from __future__ import annotations

import logging
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Raised when email sending fails."""


class EmailServiceConfigError(EmailServiceError):
    """Raised when required QQ Mail SMTP configuration is missing."""


def _mask_email(email: str) -> str:
    """Return a masked version of *email* suitable for logging.

    ``user@example.com`` → ``us***@example.com``.
    """
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"


def generate_verification_code(length: int = 6) -> str:
    """Generate a cryptographically random numeric verification code."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def send_verification_code(email: str, code: str | None = None) -> str:
    """Send a verification-code email to *email* via QQ Mail SMTP (SSL).

    If *code* is ``None`` a new 6-digit code is generated automatically.

    Returns the plain-text code that was sent so the caller can hash it
    before persistence.
    """
    if not settings.QQ_MAIL_USERNAME or not settings.QQ_MAIL_AUTH_CODE:
        raise EmailServiceConfigError(
            "QQ_MAIL_USERNAME and QQ_MAIL_AUTH_CODE must be configured "
            "in environment variables or .env file before sending emails."
        )

    if code is None:
        code = generate_verification_code()

    expire_minutes = settings.EMAIL_CODE_EXPIRE_MINUTES

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.QQ_MAIL_FROM_NAME} <{settings.QQ_MAIL_USERNAME}>"
    msg["To"] = email
    msg["Subject"] = "BusMind 注册验证码"

    body = (
        f"您好，\n\n"
        f"您的 BusMind 注册验证码是：{code}\n\n"
        f"验证码有效期为 {expire_minutes} 分钟，请尽快完成验证。\n\n"
        f"如果这不是您本人的操作，请忽略此邮件。\n\n"
        f"此致\n"
        f"BusMind 团队\n"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL(settings.QQ_MAIL_HOST, settings.QQ_MAIL_PORT) as server:
            server.login(settings.QQ_MAIL_USERNAME, settings.QQ_MAIL_AUTH_CODE)
            server.sendmail(settings.QQ_MAIL_USERNAME, email, msg.as_string())
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email to %s: %s", _mask_email(email), exc)
        raise EmailServiceError(f"Failed to send verification email: {exc}") from exc

    logger.info("Verification code sent to %s", _mask_email(email))
    return code