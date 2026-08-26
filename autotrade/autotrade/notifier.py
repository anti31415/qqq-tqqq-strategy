from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from autotrade.config import Settings


def email_configured(settings: Settings) -> bool:
    return all(
        [
            settings.notify_email_to,
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from,
        ]
    )


def build_order_email(result: dict[str, Any]) -> EmailMessage:
    msg = EmailMessage()
    response = result.get("response") or {}
    order_preview = result.get("order_preview") or {}
    candidate = result.get("candidate") or {}

    action = result.get("action", "")
    symbol = order_preview.get("symbol") or candidate.get("symbol") or response.get("symbol", "")
    qty = order_preview.get("qty", "")
    limit_price = order_preview.get("limit_price", "")
    order_id = response.get("id", "")
    status = response.get("status", "")
    timestamp = result.get("timestamp", "")

    msg["Subject"] = f"[Paper Trade] {action} {symbol}"
    body = "\n".join(
        [
            "Paper trade order submitted.",
            "",
            f"Run time: {timestamp}",
            f"Action: {action}",
            f"Option symbol: {symbol}",
            f"Quantity: {qty}",
            f"Limit price: {limit_price}",
            f"Order ID: {order_id}",
            f"Status: {status}",
        ]
    )
    msg.set_content(body)
    return msg


def send_order_email(settings: Settings, result: dict[str, Any]) -> dict[str, Any]:
    if not email_configured(settings):
        return {
            "email_attempted": False,
            "email_sent": False,
            "email_reason": "smtp_not_configured",
        }

    msg = build_order_email(result)
    msg["From"] = settings.smtp_from
    msg["To"] = settings.notify_email_to

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)

    return {
        "email_attempted": True,
        "email_sent": True,
        "email_to": settings.notify_email_to,
        "email_subject": msg["Subject"],
    }


def send_test_email(settings: Settings) -> dict[str, Any]:
    if not email_configured(settings):
        return {
            "email_attempted": False,
            "email_sent": False,
            "email_reason": "smtp_not_configured",
        }

    msg = EmailMessage()
    msg["Subject"] = "[Paper Trade] SMTP test"
    msg["From"] = settings.smtp_from
    msg["To"] = settings.notify_email_to
    msg.set_content("This is a local SMTP test from the autotrade script. No trade was placed.")

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)

    return {
        "email_attempted": True,
        "email_sent": True,
        "email_to": settings.notify_email_to,
        "email_subject": msg["Subject"],
    }
