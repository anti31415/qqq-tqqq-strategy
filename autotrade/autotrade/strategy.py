from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from autotrade.brokers.alpaca import AlpacaBroker
from autotrade.config import Settings
from autotrade.indicators import rsi, sma


@dataclass
class SignalSnapshot:
    date: str
    close: float
    previous_close: float
    sma_value: float | None
    rsi_value: float | None
    is_down_day: bool
    above_sma: bool
    rsi_below_threshold: bool
    should_open_put: bool


@dataclass
class ActionPlan:
    action: str
    reason: str
    signal: dict[str, Any]
    positions: list[dict[str, Any]]
    candidate: dict[str, Any] | None = None
    order_preview: dict[str, Any] | None = None


def latest_signal_snapshot(broker: AlpacaBroker, settings: Settings) -> SignalSnapshot:
    start = (date.today() - timedelta(days=420)).isoformat()
    end = date.today().isoformat()
    bars = broker.get_daily_bars(settings.signal_symbol, start, end)
    closes = [float(bar["c"]) for bar in bars]
    if len(closes) < settings.sma_period + 2:
        raise RuntimeError(f"Not enough bars to compute indicators for {settings.signal_symbol}")
    latest_close = closes[-1]
    previous_close = closes[-2]
    sma_value = sma(closes, settings.sma_period)
    rsi_value = rsi(closes, 14)
    is_down_day = latest_close < previous_close
    above_sma = sma_value is not None and latest_close > sma_value
    rsi_below_threshold = rsi_value is not None and rsi_value < settings.rsi_threshold
    return SignalSnapshot(
        date=bars[-1]["t"][:10],
        close=latest_close,
        previous_close=previous_close,
        sma_value=sma_value,
        rsi_value=rsi_value,
        is_down_day=is_down_day,
        above_sma=bool(above_sma),
        rsi_below_threshold=bool(rsi_below_threshold),
        should_open_put=bool(above_sma and rsi_below_threshold and is_down_day),
    )


def select_cash_secured_put_candidate(
    broker: AlpacaBroker,
    settings: Settings,
    underlying_price: float,
) -> dict[str, Any]:
    min_expiry = AlpacaBroker.iso_date(settings.dte_target - 7)
    max_expiry = AlpacaBroker.iso_date(settings.dte_target + 7)
    contracts = broker.get_option_contracts(settings.trade_symbol, min_expiry, max_expiry)
    snapshots = broker.get_option_chain_snapshots(settings.trade_symbol, feed="indicative")
    target_strike = underlying_price * settings.put_strike_pct

    candidates: list[dict[str, Any]] = []
    for contract in contracts:
        if contract.get("type") != "put":
            continue
        symbol = contract.get("symbol")
        strike = float(contract.get("strike_price"))
        snapshot = snapshots.get(symbol, {})
        mid_price = broker.option_mid_price(snapshot)
        if mid_price is None:
            continue
        candidates.append(
            {
                "symbol": symbol,
                "expiration_date": contract.get("expiration_date"),
                "strike_price": strike,
                "mid_price": mid_price,
                "distance_to_target": abs(strike - target_strike),
            }
        )

    if not candidates:
        raise RuntimeError("No put candidates found in the selected expiration window.")

    candidates.sort(key=lambda item: (item["distance_to_target"], item["expiration_date"], item["strike_price"]))
    return candidates[0]


def select_covered_call_candidate(
    broker: AlpacaBroker,
    settings: Settings,
    underlying_price: float,
    average_entry_price: float,
) -> dict[str, Any]:
    min_expiry = AlpacaBroker.iso_date(settings.dte_target - 7)
    max_expiry = AlpacaBroker.iso_date(settings.dte_target + 7)
    contracts = broker.get_option_contracts(settings.trade_symbol, min_expiry, max_expiry)
    snapshots = broker.get_option_chain_snapshots(settings.trade_symbol, feed="indicative")
    target_strike = max(round(average_entry_price), round(underlying_price))

    candidates: list[dict[str, Any]] = []
    for contract in contracts:
        if contract.get("type") != "call":
            continue
        symbol = contract.get("symbol")
        strike = float(contract.get("strike_price"))
        if strike < target_strike:
            continue
        snapshot = snapshots.get(symbol, {})
        mid_price = broker.option_mid_price(snapshot)
        if mid_price is None:
            continue
        candidates.append(
            {
                "symbol": symbol,
                "expiration_date": contract.get("expiration_date"),
                "strike_price": strike,
                "mid_price": mid_price,
                "distance_to_target": abs(strike - target_strike),
            }
        )

    if not candidates:
        raise RuntimeError("No covered call candidates found in the selected expiration window.")

    candidates.sort(key=lambda item: (item["distance_to_target"], item["expiration_date"], item["strike_price"]))
    return candidates[0]


def build_csp_order(candidate: dict[str, Any]) -> dict[str, Any]:
    limit_price = round(float(candidate["mid_price"]), 2)
    return {
        "symbol": candidate["symbol"],
        "qty": "1",
        "side": "sell",
        "type": "limit",
        "limit_price": f"{limit_price:.2f}",
        "time_in_force": "day",
    }


def build_covered_call_order(candidate: dict[str, Any], contracts_to_sell: int) -> dict[str, Any]:
    limit_price = round(float(candidate["mid_price"]), 2)
    return {
        "symbol": candidate["symbol"],
        "qty": str(contracts_to_sell),
        "side": "sell",
        "type": "limit",
        "limit_price": f"{limit_price:.2f}",
        "time_in_force": "day",
    }


def plan_next_action(broker: AlpacaBroker, settings: Settings) -> ActionPlan:
    signal = latest_signal_snapshot(broker, settings)
    positions = broker.get_positions()

    trade_positions = [position for position in positions if position.get("symbol") == settings.trade_symbol]
    option_positions = [position for position in positions if position.get("asset_class") == "us_option"]

    if option_positions:
        return ActionPlan(
            action="hold",
            reason="existing_option_position_detected",
            signal=signal.__dict__,
            positions=positions,
        )

    share_position = next((position for position in trade_positions if position.get("asset_class") == "us_equity"), None)
    if share_position:
        share_qty = int(abs(float(share_position.get("qty", "0"))))
        if share_qty >= 100:
            trade_bars = broker.get_daily_bars(settings.trade_symbol, start=broker.iso_date(-10), end=broker.iso_date(0))
            underlying_price = float(trade_bars[-1]["c"])
            average_entry_price = float(share_position.get("avg_entry_price", underlying_price))
            contracts_to_sell = share_qty // 100
            candidate = select_covered_call_candidate(
                broker=broker,
                settings=settings,
                underlying_price=underlying_price,
                average_entry_price=average_entry_price,
            )
            order = build_covered_call_order(candidate, contracts_to_sell)
            return ActionPlan(
                action="sell_covered_call",
                reason="long_tqqq_shares_detected_without_option_overlay",
                signal=signal.__dict__,
                positions=positions,
                candidate={
                    **candidate,
                    "contracts_to_sell": contracts_to_sell,
                    "average_entry_price": average_entry_price,
                    "share_qty": share_qty,
                },
                order_preview=order,
            )

        return ActionPlan(
            action="hold",
            reason="share_position_exists_but_less_than_100_shares",
            signal=signal.__dict__,
            positions=positions,
        )

    if signal.should_open_put:
        trade_bars = broker.get_daily_bars(settings.trade_symbol, start=broker.iso_date(-10), end=broker.iso_date(0))
        underlying_price = float(trade_bars[-1]["c"])
        candidate = select_cash_secured_put_candidate(broker, settings, underlying_price)
        order = build_csp_order(candidate)
        return ActionPlan(
            action="sell_cash_secured_put",
            reason="signal_conditions_met_and_no_open_trade_position",
            signal=signal.__dict__,
            positions=positions,
            candidate=candidate,
            order_preview=order,
        )

    return ActionPlan(
        action="hold",
        reason="signal_conditions_not_met",
        signal=signal.__dict__,
        positions=positions,
    )
