from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from zoneinfo import ZoneInfo

from autotrade.config import Settings


def append_jsonl_log(settings: Settings, record: dict[str, Any]) -> Path:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    path = settings.log_dir / "autotrade_history.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str))
        handle.write("\n")
    return path


def append_text_log(settings: Settings, record: dict[str, Any]) -> Path:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    path = settings.log_dir / "autotrade_history.txt"

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"Check time: {record.get('timestamp', '')}")
    lines.append(f"Source: {record.get('source', '')}")
    lines.append(f"Place-order requested: {record.get('place_order_requested', False)}")
    lines.append(f"Dry run: {record.get('dry_run', True)}")

    if record.get("status") == "error":
        lines.append("Execution result: error")
        lines.append(f"Error message: {record.get('message', '')}")
    else:
        signal = record.get("signal") or {}
        lines.append("Check method: fetch QQQ/TQQQ data through the Alpaca API, calculate SMA200, RSI(14), and down-day status, then evaluate current positions")
        lines.append(f"Strategy action: {record.get('action', '')}")
        lines.append(f"Action reason: {record.get('reason', '')}")
        lines.append(f"Action executed: {record.get('order_submitted', False)}")
        lines.append(f"Position count: {len(record.get('positions') or [])}")
        lines.append("")
        lines.append("Indicator snapshot:")
        lines.append(f"- Signal date: {signal.get('date', '')}")
        lines.append(f"- QQQ close: {signal.get('close', '')}")
        lines.append(f"- Prior close: {signal.get('previous_close', '')}")
        lines.append(f"- SMA200: {signal.get('sma_value', '')}")
        lines.append(f"- RSI(14): {signal.get('rsi_value', '')}")
        lines.append(f"- Down day: {signal.get('is_down_day', '')}")
        lines.append(f"- Above SMA200: {signal.get('above_sma', '')}")
        lines.append(f"- RSI below threshold: {signal.get('rsi_below_threshold', '')}")
        lines.append(f"- Put entry conditions met: {signal.get('should_open_put', '')}")

        candidate = record.get("candidate")
        if candidate:
            lines.append("")
            lines.append("Candidate contract:")
            lines.append(f"- Symbol: {candidate.get('symbol', '')}")
            lines.append(f"- Expiration: {candidate.get('expiration_date', '')}")
            lines.append(f"- Strike: {candidate.get('strike_price', '')}")
            lines.append(f"- Mid price: {candidate.get('mid_price', '')}")

        order_preview = record.get("order_preview")
        if order_preview:
            lines.append("")
            lines.append("Order preview:")
            lines.append(f"- Symbol: {order_preview.get('symbol', '')}")
            lines.append(f"- Quantity: {order_preview.get('qty', '')}")
            lines.append(f"- Side: {order_preview.get('side', '')}")
            lines.append(f"- Type: {order_preview.get('type', '')}")
            lines.append(f"- Limit price: {order_preview.get('limit_price', '')}")

        response = record.get("response")
        if response:
            lines.append("")
            lines.append("Order response:")
            lines.append(f"- Order ID: {response.get('id', '')}")
            lines.append(f"- Status: {response.get('status', '')}")
            lines.append(f"- Asset symbol: {response.get('symbol', '')}")

        lines.append("")
        lines.append("Email notification:")
        lines.append(f"- Attempted: {record.get('email_attempted', False)}")
        lines.append(f"- Sent successfully: {record.get('email_sent', False)}")
        if record.get("email_reason"):
            lines.append(f"- Reason: {record.get('email_reason', '')}")
        if record.get("email_to"):
            lines.append(f"- Recipient: {record.get('email_to', '')}")
        if record.get("email_subject"):
            lines.append(f"- Subject: {record.get('email_subject', '')}")

    lines.append("")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")
    return path
