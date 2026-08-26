from __future__ import annotations

import argparse
import json
import sys

from autotrade.brokers.alpaca import AlpacaBroker
from autotrade.brokers.ibkr import IbkrGateway
from autotrade.config import load_settings
from autotrade.notifier import send_test_email
from autotrade.runner import execute_cycle, run_schedule_loop
from autotrade.strategy import (
    build_csp_order,
    latest_signal_snapshot,
    plan_next_action,
    select_cash_secured_put_candidate,
)


def _print(data: object) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def cmd_doctor() -> int:
    settings = load_settings()
    result: dict[str, object] = {"config": {}, "brokers": {}}
    result["config"] = {
        "signal_symbol": settings.signal_symbol,
        "trade_symbol": settings.trade_symbol,
        "dry_run": settings.dry_run,
        "alpaca_has_keys": bool(settings.alpaca_api_key_id and settings.alpaca_api_secret_key),
        "ibkr_gateway_base_url": settings.ibkr_gateway_base_url,
    }
    if settings.alpaca_api_key_id and settings.alpaca_api_secret_key:
        try:
            result["brokers"]["alpaca"] = AlpacaBroker(settings).healthcheck()
        except Exception as exc:  # noqa: BLE001
            result["brokers"]["alpaca"] = {"status": "error", "message": str(exc)}
    else:
        result["brokers"]["alpaca"] = {"status": "missing_credentials"}

    try:
        result["brokers"]["ibkr"] = IbkrGateway(settings).healthcheck()
    except Exception as exc:  # noqa: BLE001
        result["brokers"]["ibkr"] = {"status": "not_ready", "message": str(exc)}

    _print(result)
    return 0


def cmd_alpaca_account() -> int:
    settings = load_settings()
    broker = AlpacaBroker(settings)
    _print({
        "account": broker.get_account(),
        "clock": broker.get_clock(),
        "positions": broker.get_positions(),
    })
    return 0


def cmd_signal() -> int:
    settings = load_settings()
    broker = AlpacaBroker(settings)
    signal = latest_signal_snapshot(broker, settings)
    _print(signal.__dict__)
    return 0


def cmd_preview_csp(place_order: bool) -> int:
    settings = load_settings()
    broker = AlpacaBroker(settings)
    signal = latest_signal_snapshot(broker, settings)
    if not signal.should_open_put:
        _print(
            {
                "action": "skip",
                "reason": "signal_conditions_not_met",
                "signal": signal.__dict__,
            }
        )
        return 0

    trade_bars = broker.get_daily_bars(settings.trade_symbol, start=broker.iso_date(-10), end=broker.iso_date(0))
    underlying_price = float(trade_bars[-1]["c"])
    candidate = select_cash_secured_put_candidate(broker, settings, underlying_price)
    order = build_csp_order(candidate)

    if place_order and not settings.dry_run:
        response = broker.submit_order(order)
        _print({"signal": signal.__dict__, "candidate": candidate, "order": order, "response": response})
        return 0

    _print(
        {
            "signal": signal.__dict__,
            "candidate": candidate,
            "order_preview": order,
            "place_order_requested": place_order,
            "dry_run": settings.dry_run,
            "note": "No order sent. Set DRY_RUN=false in .env and pass --place-order to submit.",
        }
    )
    return 0


def cmd_plan(place_order: bool) -> int:
    settings = load_settings()
    result = execute_cycle(settings=settings, place_order=place_order, source="cli-plan")
    _print(result)
    return 0


def cmd_schedule(place_order: bool, times_arg: str) -> int:
    settings = load_settings()
    times_of_day = [item.strip() for item in times_arg.split(",") if item.strip()]
    run_schedule_loop(settings=settings, place_order=place_order, times_of_day=times_of_day)
    return 0


def cmd_test_email() -> int:
    settings = load_settings()
    result = send_test_email(settings)
    _print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autotrade CLI for the QQQ/TQQQ strategy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check broker connectivity and local config")
    subparsers.add_parser("alpaca-account", help="Show Alpaca paper account, clock, and positions")
    subparsers.add_parser("signal", help="Evaluate the latest QQQ signal")
    preview = subparsers.add_parser("preview-csp", help="Preview the next Alpaca paper CSP order")
    preview.add_argument("--place-order", action="store_true", help="Submit the order if DRY_RUN=false")
    plan = subparsers.add_parser("plan", help="Decide whether to sell a CSP, sell a covered call, or hold")
    plan.add_argument("--place-order", action="store_true", help="Submit the planned order if DRY_RUN=false")
    schedule = subparsers.add_parser("schedule", help="Run the strategy on a local schedule and log every cycle")
    schedule.add_argument("--place-order", action="store_true", help="Submit planned orders if DRY_RUN=false")
    schedule.add_argument("--times", default="09:40,15:45", help="Comma-separated HH:MM local times")
    subparsers.add_parser("test-email", help="Send a local SMTP test email without placing any trade")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "alpaca-account":
        return cmd_alpaca_account()
    if args.command == "signal":
        return cmd_signal()
    if args.command == "preview-csp":
        return cmd_preview_csp(place_order=args.place_order)
    if args.command == "plan":
        return cmd_plan(place_order=args.place_order)
    if args.command == "schedule":
        return cmd_schedule(place_order=args.place_order, times_arg=args.times)
    if args.command == "test-email":
        return cmd_test_email()
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
