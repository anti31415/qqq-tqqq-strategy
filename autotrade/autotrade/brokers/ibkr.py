from __future__ import annotations

from typing import Any

from autotrade.config import Settings
from autotrade.http import HttpClient


class IbkrGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = HttpClient(verify_ssl=False)

    def auth_status(self) -> dict[str, Any]:
        return self.http.request(
            "GET",
            f"{self.settings.ibkr_gateway_base_url}/iserver/auth/status",
            headers={"Accept": "application/json"},
        ).data

    def healthcheck(self) -> dict[str, Any]:
        data = self.auth_status()
        return {
            "broker": "ibkr",
            "status": "ok",
            "connected": data.get("authenticated"),
            "competing": data.get("competing"),
            "connected_to_brokerage": data.get("connected"),
            "message": data.get("message"),
        }
