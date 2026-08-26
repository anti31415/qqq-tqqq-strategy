from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from autotrade.config import Settings
from autotrade.http import HttpClient


class AlpacaBroker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = HttpClient()
        self.trade_headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key_id,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key,
        }
        self.data_headers = dict(self.trade_headers)

    def _require_credentials(self) -> None:
        if not self.settings.alpaca_api_key_id or not self.settings.alpaca_api_secret_key:
            raise RuntimeError("Missing Alpaca credentials. Fill ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY in .env")

    def healthcheck(self) -> dict[str, Any]:
        self._require_credentials()
        account = self.get_account()
        clock = self.get_clock()
        return {
            "broker": "alpaca",
            "status": "ok",
            "account_status": account.get("status"),
            "paper": account.get("account_number", "").startswith("PA") or self.settings.alpaca_api_base_url.startswith("https://paper-"),
            "clock": {
                "is_open": clock.get("is_open"),
                "timestamp": clock.get("timestamp"),
                "next_open": clock.get("next_open"),
                "next_close": clock.get("next_close"),
            },
        }

    def get_account(self) -> dict[str, Any]:
        self._require_credentials()
        return self.http.request("GET", f"{self.settings.alpaca_api_base_url}/v2/account", headers=self.trade_headers).data

    def get_clock(self) -> dict[str, Any]:
        self._require_credentials()
        return self.http.request("GET", f"{self.settings.alpaca_api_base_url}/v2/clock", headers=self.trade_headers).data

    def get_positions(self) -> list[dict[str, Any]]:
        self._require_credentials()
        return self.http.request("GET", f"{self.settings.alpaca_api_base_url}/v2/positions", headers=self.trade_headers).data

    def get_daily_bars(self, symbol: str, start: str, end: str) -> list[dict[str, Any]]:
        response = self.http.request(
            "GET",
            f"{self.settings.alpaca_data_base_url}/v2/stocks/{symbol}/bars",
            headers=self.data_headers,
            params={
                "timeframe": "1Day",
                "adjustment": "all",
                "start": f"{start}T00:00:00Z",
                "end": f"{end}T23:59:59Z",
                "feed": "iex",
                "limit": 10000,
            },
        ).data
        return response.get("bars", [])

    def get_option_contracts(self, underlying_symbol: str, expiration_date_gte: str, expiration_date_lte: str) -> list[dict[str, Any]]:
        response = self.http.request(
            "GET",
            f"{self.settings.alpaca_api_base_url}/v2/options/contracts",
            headers=self.trade_headers,
            params={
                "underlying_symbols": underlying_symbol,
                "status": "active",
                "expiration_date_gte": expiration_date_gte,
                "expiration_date_lte": expiration_date_lte,
                "limit": 1000,
            },
        ).data
        return response.get("option_contracts", [])

    def get_option_chain_snapshots(self, underlying_symbol: str, feed: str = "indicative") -> dict[str, Any]:
        response = self.http.request(
            "GET",
            f"{self.settings.alpaca_data_base_url}/v1beta1/options/snapshots/{underlying_symbol}",
            headers=self.data_headers,
            params={"feed": feed, "limit": 1000},
        ).data
        return response.get("snapshots", {})

    def submit_order(self, order: dict[str, Any]) -> dict[str, Any]:
        self._require_credentials()
        return self.http.request(
            "POST",
            f"{self.settings.alpaca_api_base_url}/v2/orders",
            headers=self.trade_headers,
            json_body=order,
        ).data

    @staticmethod
    def option_mid_price(snapshot: dict[str, Any]) -> float | None:
        quote = snapshot.get("latestQuote") or snapshot.get("latest_quote") or {}
        bid = quote.get("bp") or quote.get("bid_price")
        ask = quote.get("ap") or quote.get("ask_price")
        if bid is None or ask is None:
            trade = snapshot.get("latestTrade") or snapshot.get("latest_trade") or {}
            price = trade.get("p") or trade.get("price")
            return float(price) if price is not None else None
        return (float(bid) + float(ask)) / 2

    @staticmethod
    def iso_date(days_from_today: int) -> str:
        return (date.today() + timedelta(days=days_from_today)).isoformat()
