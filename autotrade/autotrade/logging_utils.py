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
    lines.append(f"检查时间: {record.get('timestamp', '')}")
    lines.append(f"执行来源: {record.get('source', '')}")
    lines.append(f"是否请求下单: {record.get('place_order_requested', False)}")
    lines.append(f"是否 Dry Run: {record.get('dry_run', True)}")

    if record.get("status") == "error":
        lines.append("执行结果: error")
        lines.append(f"错误信息: {record.get('message', '')}")
    else:
        signal = record.get("signal") or {}
        lines.append("检查方式: 通过 Alpaca API 获取 QQQ/TQQQ 数据，计算 SMA200、RSI(14)、是否收阴，再结合当前持仓判断动作")
        lines.append(f"策略动作: {record.get('action', '')}")
        lines.append(f"动作原因: {record.get('reason', '')}")
        lines.append(f"是否执行动作: {record.get('order_submitted', False)}")
        lines.append(f"当前持仓数: {len(record.get('positions') or [])}")
        lines.append("")
        lines.append("指标快照:")
        lines.append(f"- 信号日期: {signal.get('date', '')}")
        lines.append(f"- QQQ 收盘价: {signal.get('close', '')}")
        lines.append(f"- 前一日收盘价: {signal.get('previous_close', '')}")
        lines.append(f"- SMA200: {signal.get('sma_value', '')}")
        lines.append(f"- RSI(14): {signal.get('rsi_value', '')}")
        lines.append(f"- 是否收阴: {signal.get('is_down_day', '')}")
        lines.append(f"- 是否站上 SMA200: {signal.get('above_sma', '')}")
        lines.append(f"- RSI 是否低于阈值: {signal.get('rsi_below_threshold', '')}")
        lines.append(f"- 是否满足开 Put 条件: {signal.get('should_open_put', '')}")

        candidate = record.get("candidate")
        if candidate:
            lines.append("")
            lines.append("候选合约:")
            lines.append(f"- 合约代码: {candidate.get('symbol', '')}")
            lines.append(f"- 到期日: {candidate.get('expiration_date', '')}")
            lines.append(f"- 行权价: {candidate.get('strike_price', '')}")
            lines.append(f"- 中间价: {candidate.get('mid_price', '')}")

        order_preview = record.get("order_preview")
        if order_preview:
            lines.append("")
            lines.append("订单预览:")
            lines.append(f"- 标的: {order_preview.get('symbol', '')}")
            lines.append(f"- 数量: {order_preview.get('qty', '')}")
            lines.append(f"- 方向: {order_preview.get('side', '')}")
            lines.append(f"- 类型: {order_preview.get('type', '')}")
            lines.append(f"- 限价: {order_preview.get('limit_price', '')}")

        response = record.get("response")
        if response:
            lines.append("")
            lines.append("订单返回:")
            lines.append(f"- 订单ID: {response.get('id', '')}")
            lines.append(f"- 状态: {response.get('status', '')}")
            lines.append(f"- 资产代码: {response.get('symbol', '')}")

        lines.append("")
        lines.append("邮件通知:")
        lines.append(f"- 是否尝试发送: {record.get('email_attempted', False)}")
        lines.append(f"- 是否发送成功: {record.get('email_sent', False)}")
        if record.get("email_reason"):
            lines.append(f"- 说明: {record.get('email_reason', '')}")
        if record.get("email_to"):
            lines.append(f"- 收件人: {record.get('email_to', '')}")
        if record.get("email_subject"):
            lines.append(f"- 邮件标题: {record.get('email_subject', '')}")

    lines.append("")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")
    return path
