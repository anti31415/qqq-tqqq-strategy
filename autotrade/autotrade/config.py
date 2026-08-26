from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    alpaca_api_key_id: str
    alpaca_api_secret_key: str
    alpaca_api_base_url: str
    alpaca_data_base_url: str
    ibkr_gateway_base_url: str
    signal_symbol: str
    trade_symbol: str
    dte_target: int
    put_strike_pct: float
    rsi_threshold: float
    sma_period: int
    dry_run: bool
    market_timezone: str
    notify_email_to: str
    smtp_host: str
    smtp_port: int
    smtp_use_ssl: bool
    smtp_username: str
    smtp_password: str
    smtp_from: str
    root_dir: Path
    log_dir: Path


def load_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[1]
    _load_env_file(root_dir / ".env")
    return Settings(
        alpaca_api_key_id=os.getenv("ALPACA_API_KEY_ID", ""),
        alpaca_api_secret_key=os.getenv("ALPACA_API_SECRET_KEY", ""),
        alpaca_api_base_url=os.getenv("ALPACA_API_BASE_URL", "https://paper-api.alpaca.markets"),
        alpaca_data_base_url=os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets"),
        ibkr_gateway_base_url=os.getenv("IBKR_GATEWAY_BASE_URL", "https://localhost:5000/v1/api"),
        signal_symbol=os.getenv("STRATEGY_UNDERLYING_SIGNAL", "QQQ"),
        trade_symbol=os.getenv("STRATEGY_UNDERLYING_TRADE", "TQQQ"),
        dte_target=int(os.getenv("STRATEGY_DTE_TARGET", "33")),
        put_strike_pct=float(os.getenv("STRATEGY_PUT_STRIKE_PCT", "0.92")),
        rsi_threshold=float(os.getenv("STRATEGY_RSI_THRESHOLD", "50")),
        sma_period=int(os.getenv("STRATEGY_SMA_PERIOD", "200")),
        dry_run=_bool_env("DRY_RUN", True),
        market_timezone=os.getenv("MARKET_TIMEZONE", "America/New_York"),
        notify_email_to=os.getenv("NOTIFY_EMAIL_TO", ""),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_use_ssl=_bool_env("SMTP_USE_SSL", True),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
        root_dir=root_dir,
        log_dir=root_dir / "logs",
    )
