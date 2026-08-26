from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from zoneinfo import ZoneInfo

from autotrade.brokers.alpaca import AlpacaBroker
from autotrade.config import Settings
from autotrade.logging_utils import append_jsonl_log, append_text_log
from autotrade.notifier import send_order_email
from autotrade.strategy import plan_next_action


def execute_cycle(settings: Settings, place_order: bool, source: str) -> dict[str, Any]:
    broker = AlpacaBroker(settings)
    timestamp = datetime.now(ZoneInfo(settings.market_timezone)).isoformat()
    try:
        plan = plan_next_action(broker, settings)
        result: dict[str, Any] = {
            "timestamp": timestamp,
            "source": source,
            "action": plan.action,
            "reason": plan.reason,
            "signal": plan.signal,
            "positions": plan.positions,
            "candidate": plan.candidate,
            "order_preview": plan.order_preview,
            "place_order_requested": place_order,
            "dry_run": settings.dry_run,
            "order_submitted": False,
        }
        if place_order and plan.order_preview and not settings.dry_run:
            response = broker.submit_order(plan.order_preview)
            result["response"] = response
            result["order_submitted"] = True
            email_result = send_order_email(settings, result)
            result.update(email_result)
        else:
            result.update(
                {
                    "email_attempted": False,
                    "email_sent": False,
                    "email_reason": "order_not_submitted",
                }
            )

        log_path = append_jsonl_log(settings, result)
        text_log_path = append_text_log(settings, result)
        result["log_file"] = str(log_path)
        result["text_log_file"] = str(text_log_path)
        return result
    except Exception as exc:  # noqa: BLE001
        error_result = {
            "timestamp": timestamp,
            "source": source,
            "status": "error",
            "message": str(exc),
            "place_order_requested": place_order,
            "dry_run": settings.dry_run,
            "email_attempted": False,
            "email_sent": False,
            "email_reason": "execution_error",
        }
        log_path = append_jsonl_log(settings, error_result)
        text_log_path = append_text_log(settings, error_result)
        error_result["log_file"] = str(log_path)
        error_result["text_log_file"] = str(text_log_path)
        return error_result


def run_schedule_loop(settings: Settings, place_order: bool, times_of_day: list[str], poll_seconds: int = 20) -> None:
    tz = ZoneInfo(settings.market_timezone)
    executed_slots: set[str] = set()
    while True:
        now = datetime.now(tz)
        weekday = now.weekday()
        current_key = now.strftime("%Y-%m-%d %H:%M")

        if weekday < 5 and now.strftime("%H:%M") in times_of_day and current_key not in executed_slots:
            result = execute_cycle(settings=settings, place_order=place_order, source="schedule-loop")
            append_jsonl_log(
                settings,
                {
                    "timestamp": datetime.now(tz).isoformat(),
                    "source": "schedule-loop",
                    "status": "triggered",
                    "slot": now.strftime("%H:%M"),
                    "result_action": result.get("action"),
                    "order_submitted": result.get("order_submitted"),
                    "log_file": result.get("log_file"),
                },
            )
            executed_slots.add(current_key)

        stale_prefix = now.strftime("%Y-%m-%d")
        executed_slots = {slot for slot in executed_slots if slot.startswith(stale_prefix)}
        time.sleep(poll_seconds)
