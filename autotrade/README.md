# Paper-Trading Scaffold

This package provides a preview-first automation scaffold for the QQQ / TQQQ research framework.

## Quick start

1. Copy `.env.example` to a local `.env`.
2. Add paper-account credentials.
3. Run `python -m autotrade.cli doctor`.
4. Run `python -m autotrade.cli signal` or `python -m autotrade.cli plan`.

Use an explicit place-order flag only after validating the preview. The scaffold currently supports configuration loading, signal calculation, candidate selection, order previews, Alpaca paper connectivity, and an IBKR gateway check. Assignment state, unified broker synchronization, and production alerting remain open work.

